"""
Qualifier types for function qualifiers.
"""


class QualifierType:
    """Enum for function qualifiers."""
    CONST = "const"
    NOEXCEPT = "noexcept"
    OVERRIDE = "override"
    FINAL = "final"
    CONSTEXPR = "constexpr"
    INLINE = "inline"
    STATIC = "static"
    VIRTUAL = "virtual"
    NODISCARD = "[[nodiscard]]"
    MAYBE_UNUSED = "[[maybe_unused]]"
