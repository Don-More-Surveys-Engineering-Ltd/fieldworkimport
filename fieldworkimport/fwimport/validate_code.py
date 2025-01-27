"""Functions for validating point codes in fieldwork processing."""


from typing import Optional


def _validate_single_code(
    code: str,
    previous_code: Optional[str],  # noqa: FA100
    valid_codes: list[str],
    valid_special_characters: list[str],
    parameterized_special_characters: list[str],
) -> bool:
    """Validate a single code.

    :param code: Description
    :type code: str
    :param previous_code: Description
    :type previous_code:
    :param valid_codes: Description
    :type valid_codes:
    :param valid_code_special_characters: Description
    :type valid_code_special_characters:
    """
    # Special characters can appear after a code or another special character
    if code.upper() in valid_special_characters and previous_code is not None:
        return True
    # If the previous code was a special character that is "parameterized" meaning
    # it can take paramteters like "V 0.15" where 0.15 is the param,
    # check if this code is a number. If so, it's valid.
    if previous_code and previous_code.upper() in parameterized_special_characters:
        try:
            float(code)
        except ValueError:
            pass
        else:
            return True

    # Codes need to start with a known prefix
    prefix = None
    for code_prefix in valid_codes:
        if code.upper().startswith(code_prefix):
            prefix = code_prefix
            break

    if prefix is None:
        return False

    # They may have a string starting with a number appended to the end of them, like '3B4AZ'
    suffix = code.removeprefix(prefix)
    # If there is a suffix and it doesn't start with a number, it's invalid. Otherwise, it is a valid code.
    return len(suffix) == 0 or suffix[0].isdigit()


def validate_code(
    mutlicode: str,
    valid_codes: list[str],
    valid_special_characters: list[str],
    parameterized_special_characters: list[str],
) -> bool:
    """Validate a fieldwork process point code/multicode string.

    :param mutlicode: Description
    :type mutlicode: str
    :param valid_codes: Description
    :type valid_codes:
    :param valid_code_special_characters: Description
    :type valid_code_special_characters:
    """
    # split multi code into individual codes
    codes = mutlicode.split(" ")

    # return true if all single codes are valid
    previous_code: Optional[str] = None  # noqa: FA100

    for code in codes:
        if not _validate_single_code(
            code,
            previous_code,
            valid_codes,
            valid_special_characters,
            parameterized_special_characters,
        ):
            return False
        previous_code = code

    return True
