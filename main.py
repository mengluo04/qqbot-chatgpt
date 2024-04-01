from flask import Flask, request
import requests
from openai import OpenAI

app = Flask(__name__)
# qq插件配置的正向端口
qq_host = 'http://127.0.0.1:3000'
# qq号
qq = 1263041461
# 要处理艾特消息的群号，数组，可以添加多个，英文逗号分割
allow_groups = [546393566]
# 实例化openai
# openai的key
api_key = "api_key"
# openai的代理地址，或任意符合openai接口标准的地址
base_url = 'http://127.0.0.1:8000/v1'
client = OpenAI(api_key="api_key", base_url=base_url)
# 用户的消息列表
message_dict = {
    "private": {},
    "group": {}
}


@app.route('/msg', methods=['POST'])
def handle_message():
    data = request.json
    print(data)
    post_type = data['post_type']
    # 不是文本消息，不处理
    if post_type != 'message':
        return "not text message"
    message_type = data.get('message_type', None)
    raw_message = data['raw_message']
    user_id = data['user_id']
    # 私聊，直接回复
    if message_type == 'private':
        add_history(user_id, 'private', {
            'role': 'user',
            'content': raw_message
        })
        generateAnswer(user_id, "")
    # 群里，并且是指定群里面艾特我的消息
    elif message_type == 'group' and data['group_id'] in allow_groups:
        # 拆分消息，判断是否是@消息
        arr = raw_message.split(' ')
        # 获取消息体
        content = ' '.join(arr[1:])
        info = arr[0]
        # 判断是否是艾特自己的消息
        if info == f"[CQ:at,qq={qq}]":
            add_history(user_id, 'group', {
                'role': 'user',
                'content': content
            })
            generateAnswer(user_id, data['group_id'])
    else:
        pass
    # 返回值，不重要
    return "success"


# 添加对话历史
def add_history(user_id, type, message):
    # 确保每种类型的消息都有一个以user_id为键的字典
    if user_id not in message_dict[type]:
        message_dict[type][user_id] = []

    # 将消息添加到对应用户ID的消息列表中
    message_dict[type][user_id].append(message)


# 通过user_id和type获取消息历史记录
def get_messages(user_id, type):
    # 检查user_id是否存在
    if user_id in message_dict[type]:
        # 返回对应的messages列表
        return message_dict[type][user_id]
    else:
        # 如果user_id不存在，返回None或者抛出异常
        return []


# 发送群聊消息
def send_group_msg(msg, user_id, group_id):
    data = requests.post(url=qq_host + '/send_group_msg', json={
        'group_id': group_id,
        'message': f"[CQ:at,qq={user_id}] {msg}"
    })
    print(data.text)


# 发送私聊消息
def send_private_msg(msg, user_id):
    data = requests.post(url=qq_host + '/send_private_msg', json={
        'user_id': user_id,
        'message': msg
    })
    print(data.text)


# 生成内容
def generateAnswer(user_id, group_id):
    user_messages = get_messages(user_id, 'group' if group_id else 'private')
    response = client.chat.completions.create(
        model="chatglm3-6b",
        messages=user_messages
    )
    message = response.choices[0].message
    if group_id:
        add_history(user_id, 'group', {'role': message.role, 'content': message.content})
        send_group_msg(msg=message.content, user_id=user_id, group_id=group_id)
    else:
        add_history(user_id, 'private', {'role': message.role, 'content': message.content})
        send_private_msg(message.content, user_id)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
