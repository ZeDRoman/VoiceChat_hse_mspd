import sys
import getch


def secure_password_input(prompt='Password:'):
    p_s = ''
    proxy_string = [' '] * 64
    while True:
        sys.stdout.write('\x0D' + prompt + ''.join(proxy_string))
        c = getch.getch()
        if c == '\n':
            break
        elif c == '\x7f':
            p_s = p_s[:-1]
            proxy_string[len(p_s)] = " "
        else:
            proxy_string[len(p_s)] = "*"
            p_s += c

    sys.stdout.write('\n')
    return p_s


def get_user_data():
    name = input('Username:')
    pas = secure_password_input()

    user_data = "usrData_" + name + '_' + pas

    return user_data


def get_reg_data():
    name = input('Username:')
    pas = secure_password_input()

    reg_data = "regData_" + name + '_' + pas

    return reg_data


#if __name__ == '__main__':


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
