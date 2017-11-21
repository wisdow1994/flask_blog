from flask import Blueprint

main = Blueprint('main', __name__)

from . import views, errors
from ..models import Permission


@main.app_context_processor  # 上下文处理器让变量在所有模板中可以使用
def inject_permissions():
    return dict(Permission=Permission)
