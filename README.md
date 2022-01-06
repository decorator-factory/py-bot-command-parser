# py-bot-command-parser
Parser for simple chat bot commands


# Features

- Declarative approach to parsing user commands
- Nice type inference


# Example

```py
>>> from bot_command_parser.parsers import seq, literal, word, integer
>>> quit = literal("/quit")
>>> quit.parse("/quit I'm a quitter")
("I'm a quitter", '/quit')
>>> quit.parse("nah")
SimpleParseError: Expected literal: /quit, got: nah
>>>
>>> repeat = seq + literal("/repeat") + word + integer
>>> repeat.parse("/repeat hello 5")
('', ('/repeat', 'hello', 5))
>>>
>>> repeat.parse("don't repeat yourself!")
NestedParseError: ((1,), SimpleParseError(message="Expected literal: /repeat, got: don't"))
>>>
>>> repeat.parse("/repeat Foo twice")
parsers.NestedParseError: ((3,), SimpleParseError(message='Expected an integer'))
>>>

```


# Typing

So far it only works with `pyright` because it uses bleeding-edge typing features.
But you can contribute a `mypy` plugin if you want :-)
