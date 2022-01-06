import pytest
from bot_command_parser import converters as C


# Int


def test_integer_parses_unsigned_integer():
    assert C.integer.parse("42 foo") == ("foo", 42)


def test_integer_parses_zero():
    assert C.integer.parse("0 foo") == ("foo", 0)


def test_integer_parses_negative_integer():
    assert C.integer.parse("-1234 foo") == ("foo", -1234)


def test_integer_parses_integer_with_plus():
    assert C.integer.parse("+1234 foo") == ("foo", 1234)


def test_integer_fails_if_no_integer():
    with pytest.raises(C.SimpleParseError) as e:
        C.integer.parse("oops")

    assert e.value.message == "Expected an integer"


# Word


def test_word_parses_word():
    assert C.word.parse("hello world") == ("world", "hello")


def test_word_fails_on_empty_input():
    with pytest.raises(C.SimpleParseError) as e:
        C.word.parse("")
    assert e.value.message == "Expected at least one non-space character"


def test_word_fails_on_whitespace_input():
    with pytest.raises(C.SimpleParseError) as e:
        C.word.parse("      \t\t \n")
    assert e.value.message == "Expected at least one non-space character"


# Rest


def test_rest_takes_everything():
    assert C.rest.parse(" foo bar") == ("", " foo bar")


def test_works_with_whitespace_input():
    assert C.rest.parse("   \t\n\r") == ("", "   \t\n\r")


# Nothing


def test_nothing_parses_none_and_leaves_input_intact():
    assert C.nothing.parse(" quack ") == (" quack ", None)


# Seq


def test_empty_seq_strips_initial_spaces():
    assert C.seq.parse("  hello world") == ("hello world", ())


def test_nontrivial_seq():
    parser = C.seq + C.word + C.word + C.integer + C.word
    assert parser.parse("\n hello world 42069 hehe !!!") == ("!!!", ("hello", "world", 42069, "hehe"))


def test_seq_failure_at_first_element():
    parser = C.seq + C.integer + C.integer
    with pytest.raises(C.NestedParseError) as e:
        parser.parse("not an integer")
    assert e.value == C.NestedParseError((1,), C.SimpleParseError("Expected an integer"))


def test_seq_failure_in_the_middle():
    parser = C.seq + C.integer + C.integer
    with pytest.raises(C.NestedParseError) as e:
        parser.parse("42 number")
    assert e.value == C.NestedParseError((2,), C.SimpleParseError("Expected an integer"))


def test_seq_not_enough_elements():
    parser = C.seq + C.integer + C.integer
    with pytest.raises(C.NestedParseError) as e:
        parser.parse("42")
    assert e.value == C.NestedParseError((2,), C.SimpleParseError("Expected an integer"))

# Literal


def test_literal_parses_a_literal_string():
    assert C.literal("foo").parse("foo bar baz") == ("bar baz", "foo")
