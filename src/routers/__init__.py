from importlib import import_module


__all__ = ["homework_router", "lesson_router", "user_router"]


def __getattr__(name: str):
    if name == "homework_router":
        return import_module("src.routers.Homework.router").router

    if name == "lesson_router":
        return import_module("src.routers.Lessons.router").router

    if name == "user_router":
        return import_module("src.routers.Users.router").router

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
