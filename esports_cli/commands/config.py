import click
from rich.table import Table

from esports_cli.context import pass_context
from esports_cli.utils import print_success, print_warning, print_error, print_info, console


@click.group("config")
def config_cmd():
    """账号切换与本地偏好设置"""
    pass


@config_cmd.command("show")
@pass_context
def config_show(ctx):
    """显示当前配置信息"""
    settings = ctx.settings

    table = Table(title="当前配置", show_lines=False, header_style="cyan bold", border_style="blue")
    table.add_column("配置项", style="bold")
    table.add_column("值")

    table.add_row("当前账号", ctx.current_account)
    table.add_row("账号名称", ctx.current_account_info.get("name", "-"))
    table.add_row("账号角色", ctx.current_account_info.get("role", "-"))
    table.add_row("邮箱", ctx.current_account_info.get("email", "-"))

    prefs = settings.get("preferences", {})
    table.add_row("默认赛事", prefs.get("default_tournament", "-"))
    table.add_row("日期格式", prefs.get("date_format", "-"))
    table.add_row("表格样式", prefs.get("table_style", "-"))
    table.add_row("时区", prefs.get("timezone", "-"))

    console.print(table)


@config_cmd.group("account")
def account_cmd():
    """账号管理"""
    pass


@account_cmd.command("list")
@pass_context
def account_list(ctx):
    """列出所有账号"""
    accounts = ctx.settings.get("accounts", {})
    current = ctx.current_account

    table = Table(title="账号列表", show_lines=True, header_style="cyan bold", border_style="blue")
    table.add_column("账号ID", style="bold")
    table.add_column("名称")
    table.add_column("角色")
    table.add_column("邮箱")
    table.add_column("当前")

    for acc_id, acc_info in accounts.items():
        is_current = "✓" if acc_id == current else ""
        table.add_row(
            acc_id,
            acc_info.get("name", "-"),
            acc_info.get("role", "-"),
            acc_info.get("email", "-"),
            is_current,
        )

    console.print(table)


@account_cmd.command("switch")
@click.argument("account_id")
@pass_context
def account_switch(ctx, account_id):
    """切换当前账号"""
    accounts = ctx.settings.get("accounts", {})
    if account_id not in accounts:
        print_error(f"账号 '{account_id}' 不存在")
        return

    ctx.settings["current_account"] = account_id
    ctx.save_settings()
    print_success(f"已切换到账号: {account_id} ({accounts[account_id].get('name', '')})")


@account_cmd.command("add")
@click.argument("account_id")
@click.option("--name", "-n", required=True, help="账号名称")
@click.option("--role", "-r", default="manager", help="角色: admin/manager/analyst")
@click.option("--email", "-e", default="", help="邮箱地址")
@pass_context
def account_add(ctx, account_id, name, role, email):
    """添加新账号"""
    accounts = ctx.settings.setdefault("accounts", {})
    if account_id in accounts:
        print_error(f"账号 '{account_id}' 已存在")
        return

    accounts[account_id] = {
        "name": name,
        "role": role,
        "email": email,
    }
    ctx.save_settings()
    print_success(f"账号 '{account_id}' 添加成功")


@account_cmd.command("remove")
@click.argument("account_id")
@pass_context
def account_remove(ctx, account_id):
    """删除账号"""
    accounts = ctx.settings.get("accounts", {})
    if account_id not in accounts:
        print_error(f"账号 '{account_id}' 不存在")
        return

    if account_id == ctx.current_account:
        print_error("不能删除当前正在使用的账号")
        return

    del accounts[account_id]
    ctx.save_settings()
    print_success(f"账号 '{account_id}' 已删除")


@config_cmd.group("set")
def set_cmd():
    """设置偏好选项"""
    pass


@set_cmd.command("tournament")
@click.argument("tournament_id")
@pass_context
def set_tournament(ctx, tournament_id):
    """设置默认赛事"""
    prefs = ctx.settings.setdefault("preferences", {})
    prefs["default_tournament"] = tournament_id
    ctx.save_settings()
    print_success(f"默认赛事已设置为: {tournament_id}")


@set_cmd.command("date-format")
@click.argument("format_str", type=click.Choice(["YYYY-MM-DD", "YYYY/MM/DD", "MM-DD", "MM/DD"]))
@pass_context
def set_date_format(ctx, format_str):
    """设置日期显示格式"""
    prefs = ctx.settings.setdefault("preferences", {})
    prefs["date_format"] = format_str
    ctx.save_settings()
    print_success(f"日期格式已设置为: {format_str}")


@set_cmd.command("table-style")
@click.argument("style", type=click.Choice(["rich", "simple", "grid"]))
@pass_context
def set_table_style(ctx, style):
    """设置表格样式"""
    prefs = ctx.settings.setdefault("preferences", {})
    prefs["table_style"] = style
    ctx.save_settings()
    print_success(f"表格样式已设置为: {style}")


@set_cmd.command("timezone")
@click.argument("timezone_str")
@pass_context
def set_timezone(ctx, timezone_str):
    """设置时区"""
    prefs = ctx.settings.setdefault("preferences", {})
    prefs["timezone"] = timezone_str
    ctx.save_settings()
    print_success(f"时区已设置为: {timezone_str}")
