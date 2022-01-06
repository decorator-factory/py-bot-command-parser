import pytest
from bot_command_parser import parsers as P


# Int


def test_integer_parses_unsigned_integer():
    assert P.integer.parse("42 foo") == ("foo", 42)


def test_integer_parses_zero():
    assert P.integer.parse("0 foo") == ("foo", 0)


def test_integer_parses_negative_integer():
    assert P.integer.parse("-1234 foo") == ("foo", -1234)


def test_integer_parses_integer_with_plus():
    assert P.integer.parse("+1234 foo") == ("foo", 1234)


def test_integer_fails_if_no_integer():
    with pytest.raises(P.SimpleParseError) as e:
        P.integer.parse("oops")

    assert e.value.message == "Expected an integer"


# Word


def test_word_parses_word():
    assert P.word.parse("hello world") == ("world", "hello")


def test_word_fails_on_empty_input():
    with pytest.raises(P.SimpleParseError) as e:
        P.word.parse("")
    assert e.value.message == "Expected at least one non-space character"


def test_word_fails_on_whitespace_input():
    with pytest.raises(P.SimpleParseError) as e:
        P.word.parse("      \t\t \n")
    assert e.value.message == "Expected at least one non-space character"


# Rest


def test_rest_takes_everything():
    assert P.rest.parse(" foo bar") == ("", " foo bar")


def test_works_with_whitespace_input():
    assert P.rest.parse("   \t\n\r") == ("", "   \t\n\r")


# Nothing


def test_nothing_parses_none_and_leaves_input_intact():
    assert P.nothing.parse(" quack ") == (" quack ", None)


# Seq


def test_empty_seq_strips_initial_spaces():
    assert P.seq.parse("  hello world") == ("hello world", ())


def test_nontrivial_seq():
    parser = P.seq + P.word + P.word + P.integer + P.word
    assert parser.parse("\n hello world 42069 hehe !!!") == ("!!!", ("hello", "world", 42069, "hehe"))


def test_seq_failure_at_first_element():
    parser = P.seq + P.integer + P.integer
    with pytest.raises(P.NestedParseError) as e:
        parser.parse("not an integer")
    assert e.value == P.NestedParseError((1,), P.SimpleParseError("Expected an integer"))


def test_seq_failure_in_the_middle():
    parser = P.seq + P.integer + P.integer
    with pytest.raises(P.NestedParseError) as e:
        parser.parse("42 number")
    assert e.value == P.NestedParseError((2,), P.SimpleParseError("Expected an integer"))


def test_seq_not_enough_elements():
    parser = P.seq + P.integer + P.integer
    with pytest.raises(P.NestedParseError) as e:
        parser.parse("42")
    assert e.value == P.NestedParseError((2,), P.SimpleParseError("Expected an integer"))

# Literal


def test_literal_parses_a_literal_string():
    assert P.literal("foo").parse("foo bar baz") == ("bar baz", "foo")
