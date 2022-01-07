from collections import defaultdict
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Generic, Optional, Sequence, TypeVar, Union
if TYPE_CHECKING:
    from typing_extensions import TypeVarTuple, Unpack
else:
    from collections import defaultdict
    TypeVarTuple = lambda name: None
    Unpack = defaultdict(lambda: TypeVar("__"))


P = TypeVarTuple("P")
A = TypeVar("A", covariant=True)
B = TypeVar("B")


@dataclass(frozen=True)
class OpaqueDescription:
    message: str


@dataclass(frozen=True)
class UnionDescription:
    variants: Sequence["Description"]


@dataclass(frozen=True)
class TupleDescription:
    elements: Sequence["Description"]


@dataclass(frozen=True)
class AnnotatedDescription:
    wrapped: "Description"
    annotation: str


@dataclass(frozen=True)
class EmptyDescription:
    pass


Description = Union[
    OpaqueDescription,
    UnionDescription,
    TupleDescription,
    AnnotatedDescription,
    EmptyDescription,
]


class ParseError(ABC, Exception):
    @abstractmethod
    def describe(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def nest(self, key: object, /) -> "ParseError":
        raise NotImplementedError


@dataclass
class SimpleParseError(ParseError):
    message: str

    def __post_init__(self):
        super().__init__(self.message)

    def describe(self) -> str:
        return self.message

    def nest(self, key: object, /) -> ParseError:
        return NestedParseError((key,), self)


@dataclass
class NestedParseError(ParseError):
    path: tuple[object, ...]
    error: ParseError

    def __post_init__(self):
        super().__init__(self.path, self.error)

    def describe(self) -> str:
        path = ".".join(map(repr, self.path)) or "<root>"
        return "at {0!r}: {1!r}".format(path, self.error.describe())

    def nest(self, key: object, /) -> ParseError:
        return NestedParseError((*self.path, key), self.error)


class Parser(ABC, Generic[A]):
    @abstractmethod
    def description(self) -> Description:
        raise NotImplementedError

    @abstractmethod
    def parse(self, source: str, /) -> tuple[str, A]:
        raise NotImplementedError

    def matches(self, source: str, /) -> bool:
        try:
            self.parse(source)
        except ParseError:
            return False
        else:
            return True

    def map(self, fn: Callable[[A], B]) -> "MappingParser[A, B]":
        return MappingParser(self, fn)

    def flatten(self: "Parser[Parser[B]]") -> "NestedParser[B]":
        return NestedParser(self)

    def flat_map(self, fn: Callable[[A], "Parser[B]"]) -> "FlatMappingParser[A, B]":
        return FlatMappingParser(self, fn)


@dataclass(frozen=True)
class PureParser(Parser[A]):
    value: A
    note: Optional[str] = None

    def description(self) -> Description:
        if self.note is None:
            return EmptyDescription()
        return OpaqueDescription(self.note)

    def parse(self, source: str, /) -> tuple[str, A]:
        return source, self.value


@dataclass(frozen=True)
class MappingParser(Generic[A, B], Parser[B]):
    wrapped: Parser[A]
    mapper: Callable[[A], B]

    def description(self) -> Description:
        return self.wrapped.description()

    def parse(self, source: str, /) -> tuple[str, B]:
        rest, value = self.wrapped.parse(source)
        return rest, self.mapper(value)


@dataclass(frozen=True)
class NestedParser(Parser[A]):
    wrapped: Parser[Parser[A]]

    def description(self) -> Description:
        return self.wrapped.description()

    def parse(self, source: str, /) -> tuple[str, A]:
        rest, parser = self.wrapped.parse(source)
        rest2, value = parser.parse(rest)
        return rest2, value


@dataclass(frozen=True)
class FlatMappingParser(Generic[A, B], Parser[B]):
    wrapped: Parser[A]
    mapper: Callable[[A], Parser[B]]

    def description(self) -> Description:
        return self.wrapped.description()

    def parse(self, source: str, /) -> tuple[str, B]:
        return self.wrapped.map(self.mapper).flatten().parse(source)


@dataclass(frozen=True)
class Int(Parser[int]):
    def description(self) -> Description:
        return OpaqueDescription("signed integer")

    def parse(self, source: str, /) -> tuple[str, int]:
        source = source.lstrip()
        match = re.match(r"([-+]?\d+)", source)
        if match is None:
            raise SimpleParseError("Expected an integer")
        number = int(match[1])
        rest = source[match.end(1):].lstrip()
        return rest, number


@dataclass(frozen=True)
class Word(Parser[str]):
    def description(self) -> Description:
        return OpaqueDescription("word (without spaces)")

    def parse(self, source: str, /) -> tuple[str, str]:
        source = source.lstrip()
        match = re.match(r"(\S+)", source)
        if match is None:
            raise SimpleParseError("Expected at least one non-space character")
        word = match[1]
        rest = source[match.end(1):].lstrip()
        return rest, word


@dataclass(frozen=True)
class Rest(Parser[str]):
    def description(self) -> Description:
        return OpaqueDescription("rest of the string")

    def parse(self, source: str, /) -> tuple[str, str]:
        return "", source


@dataclass(frozen=True)
class Nothing(Parser[None]):
    def description(self) -> Description:
        return EmptyDescription()

    def parse(self, source: str, /) -> tuple[str, None]:
        return source, None


@dataclass(frozen=True)
class Seq(Generic[Unpack[P]], Parser[tuple[Unpack[P]]]):
    _converters: tuple[Parser[Any], ...] = ()  # tuple[Converter[T] for T in P]

    if TYPE_CHECKING:
        def __new__(cls) -> "Seq[()]": ...
        def __init__(self) -> None: ...

    def description(self) -> Description:
        return AnnotatedDescription(
            TupleDescription([conv.description() for conv in self._converters]),
            annotation="greedy",
        )

    def parse(self, source: str, /) -> tuple[str, tuple[Unpack[P]]]:
        results: list[Any] = []

        rest = source.lstrip()
        for pos, converter in enumerate(self._converters, start=1):
            try:
                rest, parsed = converter.parse(rest)
                results.append(parsed)
            except ParseError as e:
                raise e.nest(pos)

        return rest.lstrip(), tuple(results)  # type: ignore

    def add(self, converter: Parser[A]) -> "Seq[Unpack[P], A]":
        return Seq((*self._converters, converter))  # type: ignore

    def __add__(self, converter: Parser[A]) -> "Seq[Unpack[P], A]":
        return self.add(converter)


@dataclass(frozen=True)
class Lit(Parser[str]):
    value: str

    def __post_init__(self):
        if __debug__ and any(map(str.isspace, self.value)):
            raise ValueError("Literal cannot contain spaces")

    def description(self) -> Description:
        return OpaqueDescription("literal {0!r}".format(self.value))

    def parse(self, source: str, /) -> tuple[str, str]:
        source = source.lstrip()
        match = re.match(r"(\S+)", source)
        if match is None:
            raise SimpleParseError("Expected literal: {0}".format(self.value))
        word = match[1]
        if word != self.value:
            raise SimpleParseError("Expected literal: {0}, got: {1}".format(self.value, word))
        rest = source[match.end(1):].lstrip()
        return rest, word  # type: ignore


integer = Int()
word = Word()
rest = Rest()
nothing = Nothing()
seq = Seq()
literal = Lit
pure = PureParser
