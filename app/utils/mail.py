import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import markdown


def send_email(sender_email, sender_password, receiver_email, subject, body):
    """
    send_email 的 Docstring

    :param sender_email: 发件人邮箱
    :param sender_password: 发件人密码/授权码
    :param receiver_email: 收件人邮箱
    :param subject: 邮件主题
    :param body: 邮件正文（Markdown 格式）
    """
    # 创建邮件对象
    message = MIMEMultipart("alternative")
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # 将 Markdown 转换为 HTML
    html_body = markdown.markdown(
        body,
        extensions=[
            "extra",  # 支持表格、脚注等扩展语法
            "codehilite",  # 代码高亮
            "nl2br",  # 换行符转换
            "sane_lists",  # 更好的列表处理
        ],
    )

    # 添加 CSS 样式使邮件更美观
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1, h2, h3, h4, h5, h6 {{
                margin-top: 24px;
                margin-bottom: 4px;
                font-weight: 600;
                line-height: 1.25;
            }}
            h1 {{ font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
            h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
            h3 {{ font-size: 1.25em; }}
            h4 {{ font-size: 1em; }}
            code {{
                background-color: #f6f8fa;
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
                font-size: 85%;
            }}
            pre {{
                background-color: #f6f8fa;
                padding: 16px;
                overflow: auto;
                border-radius: 6px;
                line-height: 1.45;
            }}
            pre code {{
                background-color: transparent;
                padding: 0;
            }}
            blockquote {{
                padding: 0 1em;
                color: #6a737d;
                border-left: 0.25em solid #dfe2e5;
                margin: 0;
            }}
            a {{
                color: #0366d6;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            ul, ol {{
                padding-left: 2em;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 16px 0;
            }}
            table th, table td {{
                padding: 6px 13px;
                border: 1px solid #dfe2e5;
            }}
            table tr {{
                background-color: #fff;
                border-top: 1px solid #c6cbd1;
            }}
            table tr:nth-child(2n) {{
                background-color: #f6f8fa;
            }}
            strong {{
                font-weight: 600;
            }}
            hr {{
                height: 0.25em;
                padding: 0;
                margin: 24px 0;
                background-color: #e1e4e8;
                border: 0;
            }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

    # 添加纯文本版本（作为备用）
    message.attach(MIMEText(body, "plain", "utf-8"))
    # 添加 HTML 版本
    message.attach(MIMEText(styled_html, "html", "utf-8"))

    server = None
    try:
        # 连接到 SMTP 服务器
        server = smtplib.SMTP_SSL("smtp.exmail.qq.com", 465)
        server.login(sender_email, sender_password)

        # 发送邮件
        server.send_message(message)
        print("邮件发送成功!")

    except Exception as e:
        print(f"邮件发送失败: {e}")
    finally:
        if server is not None:
            server.quit()


# 使用示例
if __name__ == "__main__":
    send_email(
        sender_email="rbmom@ronbaymat.com",
        sender_password="GY4.0-mom",
        receiver_email=",".join(["lixin02@ronbaymat.com"]),
        subject="测试邮件",
        body="""
#### (1) 2026年将发布人形机器人与具身智能综合标准化体系建设指南
**关键词：**null
**摘要：**2025年1月21日，工业和信息化部副部长张云明在国新办新闻发布会上介绍了我国人形机器人产业的发展进展。2025年国内整机企业数量已超过140家，发布产品超330款。未来工信部将从技术攻关、安全保障和生态建设三方面持续推动产业发展：一是通过“揭榜挂帅”和国家科技重大项目提升大模型、一体化关节、算力芯片等核心技术；二是加强产品质量、网络与数据安全检测，开展科技伦理研究与管理；三是强化国家人工智能产业投资基金支持，建设开源社区，并计划于2026年发布《人形机器人与具身智能综合标准化体系建设指南》，以标准化推动创新成果全球共享，以人形机器人为切入点带动具身智能大产业发展。
**链接：**http://www.china-cer.com.cn/guwen/2026012131297.html

""",
    )
