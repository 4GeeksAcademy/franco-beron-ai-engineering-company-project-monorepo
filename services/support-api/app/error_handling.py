from contextlib import contextmanager
import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


logger = logging.getLogger(__name__)


@contextmanager
def operation_errors(session=None):
    try:
        yield
    except HTTPException:
        raise
    except Exception as error:
        if session is not None:
            try:
                session.rollback()
            except SQLAlchemyError:
                logger.error("database_rollback_failed")
        logger.error("operation_failed type=%s", type(error).__name__)
        if isinstance(error, IntegrityError):
            code, message = 400, "Los datos entran en conflicto con un registro existente. Revisa los datos."
        elif isinstance(error, SQLAlchemyError):
            code, message = 503, "El servicio está temporalmente indisponible. Inténtalo de nuevo."
        else:
            code, message = 500, "No se pudo completar la operación. Inténtalo de nuevo."
        raise HTTPException(status_code=code, detail={"error": "operation_failed", "message": message}) from None