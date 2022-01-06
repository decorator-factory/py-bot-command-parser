from bot_command_parser.parsers import seq, word, integer, literal, ParseError


quit = literal("/quit")
repeat = seq + literal("/repeat") + word + integer



print("Commands:")
print("    /quit")
print("    /repeat <word> <times>")

while True:
    try:
        command = input(">>> ")
    except (KeyboardInterrupt, EOFError):
        print("\nBye!")
        break

    if not command:
        continue

    if quit.matches(command):
        print("Bye!")
        break

    try:
        _, (_, phrase, times) = repeat.parse(command)
    except ParseError as exc:
        print(exc.describe())
    else:
        for _ in range(times):
            print(phrase)
