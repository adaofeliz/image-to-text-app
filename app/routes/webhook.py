"""Webhook routes for deployment and automation."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.dependencies.dependencies import verify_deploy_token
from app.utils.logger import logger

router = APIRouter()


@router.post("/webhook/deploy", status_code=status.HTTP_200_OK)
async def deploy_webhook(  # pylint: disable=unused-argument
    environment: str = Query("production", description="Deployment environment"),
    _token: str = Depends(verify_deploy_token),
):
    """Trigger build via webhook.

    This endpoint executes the build_web-app.sh script to build the web application image.
    Requires a valid deployment token via query parameter.
    """
    try:
        logger.info("Deployment webhook triggered for environment: %s", environment)

        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent.resolve()

        # Try multiple possible locations for build_web-app.sh
        # Priority: mounted volume path, then project root, then current directory
        possible_paths = [
            Path(
                "/app/project/build_web-app.sh"
            ),  # If running in Docker with mounted volume
            project_root
            / "build_web-app.sh",  # Standard location (relative to webhook.py)
            Path.cwd() / "build_web-app.sh",  # Current working directory
        ]

        build_script = None
        checked_paths = []
        for path in possible_paths:
            checked_paths.append(str(path))
            try:
                resolved_path = path.resolve()
                if resolved_path.exists() and resolved_path.is_file():
                    build_script = resolved_path
                    logger.info("Found build_web-app.sh at: %s", build_script)
                    break
            except (OSError, RuntimeError) as e:
                logger.debug("Could not resolve path %s: %s", path, e)
                continue

        if not build_script:
            error_msg = (
                f"Build script not found. Checked paths: {', '.join(checked_paths)}. "
                "Ensure build_web-app.sh is mounted as a volume or available in the project root."
            )
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

        # Execute build script asynchronously in the background
        script_working_dir = (
            Path("/app/project")
            if str(build_script).startswith("/app/project")
            else str(project_root)
        )
        logger.info(
            "Starting build script in background: %s (cwd: %s)",
            build_script,
            script_working_dir,
        )

        # Execute build script and wait for it to complete
        logger.info("Executing build script (this will build the image)...")
        process = await asyncio.create_subprocess_exec(
            str(build_script),
            environment,
            stdout=None,
            stderr=None,
            cwd=str(script_working_dir),
        )

        # Wait for build script to complete
        await process.wait()

        if process.returncode != 0:
            error_msg = f"Build failed (exit code {process.returncode})"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

        logger.info("Image build completed successfully")

        # Return success response
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Build completed successfully",
                "environment": environment,
                "status": "completed",
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


@router.post("/webhook/git/pull", status_code=status.HTTP_200_OK)
async def git_pull_webhook(  # pylint: disable=unused-argument
    _token: str = Depends(verify_deploy_token),
):
    """Trigger git pull via webhook.

    This endpoint executes the pull.sh script to pull latest changes from main branch.
    Requires a valid deployment token via query parameter.
    """
    try:
        logger.info("Git pull webhook triggered")

        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent.resolve()

        # Try multiple possible locations for pull.sh
        possible_paths = [
            Path("/app/project/pull.sh"),  # If running in Docker with mounted volume
            project_root / "pull.sh",  # Standard location (relative to webhook.py)
            Path.cwd() / "pull.sh",  # Current working directory
        ]

        pull_script = None
        checked_paths = []
        for path in possible_paths:
            checked_paths.append(str(path))
            try:
                resolved_path = path.resolve()
                if resolved_path.exists() and resolved_path.is_file():
                    pull_script = resolved_path
                    logger.info("Found pull.sh at: %s", pull_script)
                    break
            except (OSError, RuntimeError) as e:
                logger.debug("Could not resolve path %s: %s", path, e)
                continue

        if not pull_script:
            error_msg = (
                f"Pull script not found. Checked paths: {', '.join(checked_paths)}. "
                "Ensure pull.sh is mounted as a volume or available in the project root."
            )
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

        # Execute pull script asynchronously in the background
        script_working_dir = (
            Path("/app/project")
            if str(pull_script).startswith("/app/project")
            else str(project_root)
        )
        logger.info(
            "Starting pull script in background: %s (cwd: %s)",
            pull_script,
            script_working_dir,
        )

        # Output will be captured by Docker logs since we're running in a container
        process = await asyncio.create_subprocess_exec(
            str(pull_script),
            stdout=None,
            cwd=str(script_working_dir),
        )

        logger.info("Pull script started with PID: %s", process.pid)

        # Return success response immediately without waiting for completion
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Git pull triggered successfully",
                "status": "started",
                "pid": process.pid,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Git pull webhook error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Git pull webhook error: {str(exc)}",
        ) from exc
