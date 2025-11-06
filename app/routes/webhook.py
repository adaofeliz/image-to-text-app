"""Webhook routes for deployment and automation."""

import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.utils.logger import logger

router = APIRouter()


def verify_deploy_token(token: str = Query(..., description="Deployment token")):
    """Verify deployment webhook token."""
    expected_token = os.getenv("DEPLOY_WEBHOOK_TOKEN")
    if not expected_token:
        logger.warning("DEPLOY_WEBHOOK_TOKEN not set in environment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Deployment webhook is not configured",
        )
    if token != expected_token:
        logger.warning("Invalid deployment token attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid deployment token",
        )
    return token


@router.get("/webhook/deploy", status_code=status.HTTP_200_OK)
async def deploy_webhook(  # pylint: disable=unused-argument
    environment: str = Query("production", description="Deployment environment"),
    _token: str = Depends(verify_deploy_token),  # Token verified by dependency
):
    """Trigger deployment via webhook.

    This endpoint executes the deploy.sh script in the production environment.
    Requires a valid deployment token via query parameter.
    """
    try:
        logger.info("Deployment webhook triggered for environment: %s", environment)

        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent.resolve()
        deploy_script = project_root / "deploy.sh"

        if not deploy_script.exists():
            logger.error("deploy.sh script not found at: %s", deploy_script)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Deployment script not found",
            )

        # Make sure script is executable
        deploy_script.chmod(0o755)

        # Execute deployment script asynchronously
        logger.info("Executing deployment script: %s", deploy_script)
        process = await asyncio.create_subprocess_exec(
            str(deploy_script),
            environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(project_root),
        )

        # Read output and wait for process to complete
        stdout, _ = await process.communicate()
        output = stdout.decode("utf-8") if stdout else ""
        return_code = process.returncode

        if return_code != 0:
            logger.error(
                "Deployment script failed with return code %d. Output: %s",
                return_code,
                output,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Deployment failed: {output[-500:]}",  # Last 500 chars
            )

        logger.info("Deployment completed successfully")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Deployment triggered successfully",
                "environment": environment,
                "output": output,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Deployment webhook error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment webhook error: {str(exc)}",
        ) from exc
