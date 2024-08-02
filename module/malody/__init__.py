import module.malody.calc as calc

def handle_command(message):
    msg = message.split(" ", 3)
    cmd = msg[1]
    try:
        if cmd == "calc":
            return calc.return_msg(msg[2], msg[3])
        else:
            return "暂不支持相关指令"
    except Exception as e:
        message_return = repr(e)
    return message_return