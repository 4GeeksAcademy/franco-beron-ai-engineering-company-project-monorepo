/**
 * SSE (Server-Sent Events) client for real-time notifications.
 *
 * Uses fetch() + ReadableStream instead of EventSource so we can
 * send custom Authorization headers (JWT Bearer token).
 *
 * Features:
 * - JWT auth via Authorization header
 * - Automatic reconnection with exponential backoff (1s → 30s max)
 * - Last-Event-ID tracking for recovery after disconnection
 * - Deduplication of events by ticket_id
 * - Event callbacks for different event types
 */

/* ------------------------------------------------------------------ */
/*  Configuration                                                       */
/* ------------------------------------------------------------------ */

const API_BASE = (
  process.env.NEXT_PUBLIC_INVENTORY_API_URL || "/backend"
).replace(/\/$/, "");

const SSE_URL = `${API_BASE}/api/events/stream`;

const BACKOFF_INITIAL_MS = 1000;
const BACKOFF_MAX_MS = 30000;
const BACKOFF_JITTER = 0.2; // 20% jitter

/* ------------------------------------------------------------------ */
/*  SSE Client                                                          */
/* ------------------------------------------------------------------ */

export class SSEClient {
  /**
   * @param {object} options
   * @param {string} options.getToken - Function that returns the current JWT token
   * @param {object} options.handlers - Map of event name -> callback(data)
   * @param {boolean} options.debug - Enable debug logging (default: false)
   */
  constructor({ getToken, handlers = {}, debug = false }) {
    this.getToken = getToken;
    this.handlers = handlers;
    this.debug = debug;

    /** @type {AbortController|null} */
    this._abortController = null;
    this._lastEventId = null;
    this._retryCount = 0;
    this._connected = false;
    this._destroyed = false;

    /** @type {Set<string>} Set of ticket_id values already received (dedup) */
    this._seenIds = new Set();

    this._log("SSEClient created");
  }

  /* ----- Connection management ----- */

  /**
   * Start the SSE connection.
   * Returns a promise that resolves when the stream ends (on error/disconnect).
   * The client will automatically reconnect with backoff.
   */
  async connect() {
    if (this._destroyed) return;

    const token = this.getToken();
    if (!token) {
      this._log("No token available, delaying connection");
      this._scheduleReconnect();
      return;
    }

    this._abortController = new AbortController();

    const url = new URL(SSE_URL);
    if (this._lastEventId !== null) {
      url.searchParams.set("Last-Event-ID", String(this._lastEventId));
    }

    this._log(`Connecting to SSE at ${url.pathname}${url.search}`);

    try {
      const response = await fetch(url.toString(), {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "text/event-stream",
        },
        signal: this._abortController.signal,
      });

      if (!response.ok) {
        throw new Error(
          `SSE connection failed: ${response.status} ${response.statusText}`,
        );
      }

      if (!response.body) {
        throw new Error("SSE response has no readable body");
      }

      this._connected = true;
      this._retryCount = 0;
      this._log("SSE connection established");

      // Notify 'open' handler if present
      this._emitEvent("__open__", null);

      // Process the stream
      await this._readStream(response.body.getReader());
    } catch (error) {
      if (error.name === "AbortError") {
        this._log("SSE connection aborted intentionally");
        return;
      }

      this._connected = false;
      this._log(`SSE connection error: ${error.message}`);
      this._emitEvent("__error__", { message: error.message });
      this._scheduleReconnect();
    }
  }

  /**
   * Disconnect and stop reconnecting.
   */
  disconnect() {
    this._destroyed = true;
    this._connected = false;
    if (this._abortController) {
      this._abortController.abort();
      this._abortController = null;
    }
    this._log("SSEClient disconnected and destroyed");
  }

  /**
   * Get the last event ID received (for recovery after reconnect).
   */
  get lastEventId() {
    return this._lastEventId;
  }

  /**
   * Check if the client is currently connected.
   */
  get connected() {
    return this._connected;
  }

  /* ----- Stream parsing ----- */

  async _readStream(reader) {
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          this._log("SSE stream ended by server");
          this._connected = false;
          this._emitEvent("__closed__", null);
          this._scheduleReconnect();
          return;
        }

        buffer += decoder.decode(value, { stream: true });

        // Parse complete SSE messages from buffer
        const messages = buffer.split("\n\n");
        // Keep the last (possibly incomplete) chunk in the buffer
        buffer = messages.pop() || "";

        for (const message of messages) {
          if (!message.trim()) continue;
          this._parseMessage(message);
        }
      }
    } catch (error) {
      if (error.name === "AbortError") return;
      this._connected = false;
      this._log(`SSE stream read error: ${error.message}`);
      this._emitEvent("__error__", { message: error.message });
      this._scheduleReconnect();
    }
  }

  _parseMessage(raw) {
    const lines = raw.split("\n");
    let eventType = "message";
    let data = "";
    let id = null;

    for (const line of lines) {
      if (line.startsWith("id: ")) {
        id = line.slice(4).trim();
      } else if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        data = line.slice(6).trim();
      } else if (line.startsWith(":")) {
        // Comment line (keep-alive) — ignore
      }
    }

    // Update last event ID if provided
    if (id !== null) {
      this._lastEventId = parseInt(id, 10);
    }

    // Parse JSON data
    let parsedData = null;
    if (data) {
      try {
        parsedData = JSON.parse(data);
      } catch {
        this._log(`Failed to parse SSE data JSON: ${data.slice(0, 80)}`);
        return;
      }
    }

    this._log(`SSE event: ${eventType}`, parsedData);

    // Emit to registered handler
    this._emitEvent(eventType, parsedData);
  }

  /* ----- Event dispatching ----- */

  _emitEvent(eventType, data) {
    if (this._destroyed) return;

    // Deduplication: if the event has a ticket_id we've already seen, skip it
    if (data && data.ticket_id) {
      if (this._seenIds.has(data.ticket_id)) {
        this._log(`Duplicate ticket_id ${data.ticket_id}, skipping`);
        return;
      }
      // Record it after handlers have had a chance to process it
      // (we record it before so even if a handler fails, we don't re-process)
      this._seenIds.add(data.ticket_id);
    }

    const handler = this.handlers[eventType];
    if (typeof handler === "function") {
      try {
        handler(data);
      } catch (error) {
        this._log(`Handler error for event "${eventType}": ${error.message}`);
      }
    }
  }

  /* ----- Reconnection with exponential backoff ----- */

  _scheduleReconnect() {
    if (this._destroyed) return;

    this._retryCount++;
    const delay = Math.min(
      BACKOFF_INITIAL_MS * Math.pow(2, this._retryCount - 1),
      BACKOFF_MAX_MS,
    );
    // Add jitter: ±20%
    const jitter = delay * BACKOFF_JITTER * (Math.random() * 2 - 1);
    const actualDelay = Math.round(delay + jitter);

    this._log(
      `Scheduling reconnect attempt ${this._retryCount} in ${actualDelay}ms`,
    );

    setTimeout(() => {
      if (!this._destroyed) {
        this.connect();
      }
    }, actualDelay);
  }

  /* ----- Logging ----- */

  _log(...args) {
    if (this.debug) {
      console.log("[SSEClient]", ...args);
    }
  }
}

/**
 * Create an SSE client pre-configured for the Nexova backoffice.
 *
 * @param {object} options
 * @param {string} options.getToken - Function returning JWT from storage
 * @param {function} options.onRfpTicketCreated - Callback for rfp_ticket_created events
 * @param {function} options.onError - Callback for connection errors
 * @param {function} options.onReconnect - Callback when reconnecting
 * @param {boolean} options.debug - Enable debug logging
 * @returns {SSEClient}
 */
export function createBackofficeSSEClient({
  getToken,
  onRfpTicketCreated,
  onError,
  onReconnect,
  debug = false,
} = {}) {
  const client = new SSEClient({
    getToken,
    debug,
    handlers: {
      rfp_ticket_created: (data) => {
        if (typeof onRfpTicketCreated === "function") {
          onRfpTicketCreated(data);
        }
      },
      __error__: (data) => {
        if (typeof onError === "function") {
          onError(data);
        }
      },
    },
  });

  return client;
}
