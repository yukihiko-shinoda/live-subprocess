"""For testing stdout and stderr."""

import sys


def main() -> None:
    """For testing stdout and stderr."""
    count = 0
    total_number_of_std = 2
    while True:
        count = count + 1
        if count % 1 == 0:
            # Reason: To test that stdout and stderr are output in real time
            print("stdout")  # noqa: T201
        # On Windows with Python 3.9, it seems to block the output of stdout
        # when same amount of stderr is output.
        if count % total_number_of_std == 0:
            # Reason: To test that stdout and stderr are output in real time
            print("stderr", file=sys.stderr)  # noqa: T201
        if count >= total_number_of_std:
            count = 0


if __name__ == "__main__":
    main()
