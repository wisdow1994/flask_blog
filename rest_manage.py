from app import create_app
from flask import abort
from flask_restful import Api, Resource, fields, marshal_with, reqparse
from app.models import Post, User

app = create_app('default')
api = Api(app)

post_get_parser = reqparse.RequestParser()
post_get_parser.add_argument(
    'page',  # 请求中的参数
    type=int,
    location=['args', 'headers'],
    required=False
)
post_get_parser.add_argument(
    'user',
    type=str,
    location=['args', 'json', 'headers']
)

post_get_fields = {
    'body': fields.String(),
    'author': fields.String(attribute=lambda x: x.author.username),
    # 如果找到模型所对应的同名字段值,就需要明确指定指定
    'id': fields.Integer()  # 文章所属的id
}


class PostApi(Resource):
    @marshal_with(post_get_fields)
    def get(self, post_id=None):
        if post_id:
            post = Post.query.get_or_404(post_id)
            return post
        else:
            args = post_get_parser.parse_args()
            page = args['page'] or 1
            if args['user']:
                user = User.query.filter_by(username=args['user']).first()
                if not user:
                    abort(404)
                posts = user.posts.order_by(Post.timestamp.desc()).paginate(page, 20)
            else:
                posts = Post.query.order_by(Post.timestamp.desc()).paginate(page, 20)
            return posts.items


api.add_resource(PostApi, '/api/post', '/api/post/<int:post_id>', endpoint='post')


if __name__ == '__main__':
    app.run(debug=True)