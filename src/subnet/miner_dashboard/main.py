import signal
from datetime import datetime
import uvicorn
from fastapi import FastAPI, Request, Query, HTTPException, Form, Depends
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette import status
from starlette.responses import RedirectResponse

from src.subnet.miner.database.models.twitter_post import TwitterPostManager
from src.subnet.miner._config import load_environment, MinerSettings
from src.subnet.miner.database.session_manager import DatabaseSessionManager


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m miner_dashboard <environment> ; where <environment> is 'testnet' or 'mainnet'")
        sys.exit(1)

    env = sys.argv[1]
    use_testnet = env == 'testnet'
    load_environment(env)
    settings = MinerSettings()


    def patch_record(record):
        record["extra"]["service"] = 'miner_dashboard'
        record["extra"]["timestamp"] = datetime.utcnow().isoformat()
        record["extra"]["level"] = record['level'].name
        return True

    logger.remove()
    logger.add(
        "../../logs/miner_dashboard.log",
        rotation="500 MB",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        filter=patch_record
    )

    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <blue>{message}</blue> | {extra}",
        level="DEBUG",
        filter=patch_record
    )

    session_manager = DatabaseSessionManager()
    session_manager.init(settings.DATABASE_URL)
    twitter_post_manager = TwitterPostManager(session_manager)

    app = FastAPI(title="Miner Dashboard", description="Miner Dashboard")
    templates = Jinja2Templates(directory="subnet/miner_dashboard/templates")
    app.mount("/static", StaticFiles(directory="subnet/miner_dashboard/static"), name="static")

    @app.exception_handler(404)
    async def custom_404_handler(request: Request, exc: Exception):
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": "The page you are looking for does not exist."
        }, status_code=404)

    @app.exception_handler(500)
    async def custom_500_handler(request: Request, exc: Exception):
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": "An internal server error occurred. Please try again later."
        }, status_code=500)

    @app.exception_handler(400)
    async def validation_exception_handler(request: Request, exc: HTTPException):
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": f"Error: {exc.detail}"
        }, status_code=exc.status_code)


    security = HTTPBasic()

    def authenticate_user(credentials):
        if not verify_password(credentials.password, settings.DASHBOARD_USER_PASSWORD_HASH):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},  # This header triggers the browser's auth dialog
            )

    @app.get("/")
    async def master_page(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/submissions")
    async def get_submissions(request: Request, page: int = Query(1, gt=0), per_page: int = Query(5, gt=0), credentials: HTTPBasicCredentials = Depends(security)):
        authenticate_user(credentials)
        data = await twitter_post_manager.get_tweets(page=page, page_size=per_page)
        return templates.TemplateResponse("submissions.html", {
            "request": request,
            "tweets": data["tweets"],
            "page": page,
            "total_pages": data["total_pages"]
        })


    @app.get("/submit")
    async def submit_form(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
        authenticate_user(credentials)
        return templates.TemplateResponse("add_submission.html", {"request": request})


    @app.post("/submit")
    async def submit(request: Request, tweet_id: str = Form(...), dispatch_after: str = Form(...), credentials: HTTPBasicCredentials = Depends(security)):
        authenticate_user(credentials)
        try:
            dispatch_time = datetime.strptime(dispatch_after, '%Y-%m-%dT%H:%M')
            await twitter_post_manager.add_tweet(user_id=settings.USER_ID, tweet_id=tweet_id, dispatch_after=dispatch_time)
            return RedirectResponse("/submissions", status_code=303)

        except HTTPException as e:
            return templates.TemplateResponse("add_submission.html", {
                "request": request,
                "error_message": e.detail,
                "user_id": settings.USER_ID,
                "tweet_id": tweet_id,
                "dispatch_after": dispatch_after,
            })

        except Exception as e:
            return templates.TemplateResponse("add_submission.html", {
                "request": request,
                "error_message": "An unexpected error occurred. Please try again.",
                "user_id": settings.USER_ID,
                "tweet_id": tweet_id,
                "dispatch_after": dispatch_after,
            })

    @app.get("/submissions/{tweet_id}")
    async def read_submission(request: Request, tweet_id: str, credentials: HTTPBasicCredentials = Depends(security)):
        authenticate_user(credentials)
        try:
            tweet = await twitter_post_manager.get_tweet_by_id(tweet_id)
            return templates.TemplateResponse("submit.html", {
                "request": request,
                "tweet": tweet,
            })

        except HTTPException as e:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": e.detail,
            }, status_code=e.status_code)

        except Exception as e:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": "An unexpected error occurred while fetching the tweet.",
            }, status_code=500)


    @app.get("/submissions/{tweet_id}/update")
    async def update_submission_form(request: Request, tweet_id: str, credentials: HTTPBasicCredentials = Depends(security)):
        authenticate_user(credentials)
        try:
            tweet = await twitter_post_manager.get_tweet_by_id(tweet_id)
            return templates.TemplateResponse("update_submission.html", {
                "request": request,
                "tweet": tweet
            })

        except HTTPException as e:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": e.detail
            }, status_code=e.status_code)

        except Exception as e:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": "An unexpected error occurred while fetching the tweet."
            }, status_code=500)


    from dateutil import parser
    @app.post("/submissions/{tweet_id}/update")
    async def update_submission(request: Request, tweet_id: str, dispatch_after: str = Form(...), credentials: HTTPBasicCredentials = Depends(security)):
        authenticate_user(credentials)
        try:
            parsed_date = parser.parse(dispatch_after)
            await twitter_post_manager.edit_tweet(tweet_id=tweet_id, new_dispatch_after=parsed_date)
            return RedirectResponse(f"/submissions/{tweet_id}", status_code=303)

        except HTTPException as e:
            return templates.TemplateResponse("update_submission.html", {
                "request": request,
                "error_message": e.detail,
                "tweet_id": tweet_id,
                "dispatch_after": dispatch_after
            })

        except Exception as e:
            return templates.TemplateResponse("update_submission.html", {
                "request": request,
                "error_message": "An unexpected error occurred. Please try again.",
                "tweet_id": tweet_id,
                "dispatch_after": dispatch_after
            })


    @app.get("/submissions/{tweet_id}/remove")
    async def submission_remove_form(request: Request, tweet_id: str, credentials: HTTPBasicCredentials = Depends(security)):
        authenticate_user(credentials)
        try:
            tweet = await twitter_post_manager.get_tweet_by_id(tweet_id)
            return templates.TemplateResponse("remove_submission.html", {
                "request": request,
                "tweet": tweet
            })

        except HTTPException as e:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": e.detail
            }, status_code=e.status_code)

    @app.post("/submissions/{tweet_id}/remove")
    async def submission_remove(request: Request, tweet_id: str, credentials: HTTPBasicCredentials = Depends(security)):
        authenticate_user(credentials)
        try:
            await twitter_post_manager.delete_tweet(tweet_id=tweet_id)
            return RedirectResponse("/submissions", status_code=303)

        except HTTPException as e:
            # Pass the error message to the template
            return templates.TemplateResponse("remove_submission.html", {
                "request": request,
                "error_message": e.detail,
                "tweet_id": tweet_id
            })

        except Exception as e:
            return templates.TemplateResponse("remove_submission.html", {
                "request": request,
                "error_message": "An unexpected error occurred. Please try again.",
                "tweet_id": tweet_id
            })


    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    def shutdown_handler(signal, frame):
        logger.debug("Shutdown handler started")
        uvicorn_server.should_exit = True
        uvicorn_server.force_exit = True
        logger.debug("Shutdown handler finished")

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    uvicorn_server = uvicorn.Server(config=uvicorn.Config(app, host="0.0.0.0", port=settings.PORT + 1, workers=settings.WORKERS))
    uvicorn_server.run()
