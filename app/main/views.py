from flask import render_template, session, redirect, url_for, abort, flash, \
    request, current_app, make_response
from .. import db
from ..models import User, Role, Post, Permission, Comment
from ..decorators import admin_required, permission_required
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentFoem
from flask_login import login_required, current_user


@main.route('/', methods=['GET', 'POST'])
def index():  # 渲染全部文章或者登陆用户关注的文章
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and \
            form.validate_on_submit():
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['FLASKY_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    return render_template('index.html', form=form, posts=posts,
                           pagination=pagination, show_followed=show_followed)


@main.route('/all')
@login_required
def all():  # 设置cookie值
    resp = make_response(redirect(url_for('main.index')))
    resp.set_cookie('show_followed', '', max_age=15*24*60*60)
    return resp


@main.route('/followed')
@login_required
def followed():  # 设置cookie值,字符串类型
    resp = make_response(redirect(url_for('main.index')))
    resp.set_cookie('show_followed', '1', max_age=15*24*60*60)
    return resp


@main.route('/user/<username>')
def user(username):  # 用户的资料页
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts, pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():  # 修改自己的用户资料
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('你的资料修改成功.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):  # 修改用户资料,Admin才有资格
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)

        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('此用户的资料修改成功!')
        return redirect(url_for('main.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id  # 用户的当前权限,使用user的外键表示,是数字

    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me = current_user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):  # 渲染文章及评论
    post = Post.query.get_or_404(id)
    form = CommentFoem()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        flash('你的评论已经提交!')
        return redirect(url_for('main.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)  # -1 是一个特殊的页数,程序从查询字符串中获取页数
    if page == -1:
        # 发现值为-1 时，会计算评论的总量和总页数，得出真正要显示的页数
        page = (post.comments.count() - 1) // current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
        # count()-1很有必要,因为当count()的值可以整除PER_PAGE时,后面的+1操作就是多余的了
    pagination = post.comments.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items

    return render_template('post.html', posts=[post], pagination=pagination,
                           form=form, comments=comments)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):  # 文章修改
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        flash('文章已经修改!')
        return redirect(url_for('main.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html', form=form)


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):  # 关注用户操作的视图函数
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('该用户不存在!')
        return redirect(url_for('main.index'))
    if current_user.is_following(user):
        flash('你已经关注了该用户!')
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    flash(f'你已经关注了用户 {user.username}')
    return redirect(url_for('main.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):  # 取消关注操作的视图函数
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('该用户不存在!')
        return redirect(url_for('main.index'))
    if not current_user.is_following(user):
        flash('你没有关注该用户!')
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    flash(f'你已经取消关注了用户 {user.username}')
    return redirect(url_for('main.user', username=username))


@main.route('/followers/<username>')
def followers(username):  # 显示我的粉丝列表的页面
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('该用户不存在!')
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'], error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp} for item in pagination.items]
    return render_template('followers.html', user=user, title=f"{user.username}的粉丝列表",
                           endpoint='main.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed-by/<username>')
def followed_by(username):  # 显示我关注用户列表的页面
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='main.followed_by', pagination=pagination,
                           follows=follows)


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments, pagination=pagination)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):  # 让评论可用
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('main.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):  # 禁用评论
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('main.moderate',
                            page=request.args.get('page', 1, type=int)))
