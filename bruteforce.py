# /usr/bin/env python3
import subprocess
import pickle
import argparse
import itertools


ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def gen_guess_alpha_numeric(size=1, alphabet=ALPHABET):
    yield ""
    for i in range(1, size + 1):
        yield from gen_guess_exact_alpha_numeric(i, alphabet)


def gen_guess_exact_alpha_numeric(size=1, alphabet=ALPHABET):
    combinations = itertools.product(alphabet, repeat=size)
    yield from ("".join(comb) for comb in combinations)


def gen_guess_from_file(guesses_path):
    with open(guesses_path) as wordlist:
        for line in wordlist:
            if line.startswith("c"):
                yield "{} horse battery staple".format(line.rstrip())


def load_status(status_file_path, volume_path):
    status = {"success": set(), "failure": set(), "volume_path": volume_path}
    try:
        with open(status_file_path, "rb") as status_file:
            status = pickle.load(status_file)
    except FileNotFoundError:
        print("status file not found")
        return status

    if status["volume_path"] != volume_path:
        print(
            "targeting volume '{volume_path}' but status file is for '{}'".format(
                volume_path, status["volume_path"]
            )
        )
        exit(1)

    if status["success"]:
        print(
            "successful passwords already known: {}".format(status["success"])
        )
        print("use a different status file to search again")
        exit(0)

    return status


def dump_status(status_file_path, status):
    with open(status_file_path, "wb") as status_file:
        pickle.dump(status, status_file)


def make_guess(volume_path, mount_path, status, guess):
    try:
        print("trying '{}'".format(guess))
        # TODO: call is not working
        subprocess.check_call(
            [
                "veracrypt",
                "--text",  # Uses the text interface
                "--password={}".format(guess),
                "--protect-hidden=no",
                "--keyfiles=",
                # Prevents re-prompting for passphrase on failure.
                "--non-interactive",
                # 485 is the default for most devices.
                # "--pim=485",
                volume_path,
                mount_path,
            ],
            # Timeout allows faster guesses but may risk false negatives.
            # Added based on noticing that a failed password
            # takes much longer than a successful one.
            # timeout=2
        )
        print("'{}' worked".format(guess))
        status["success"].add(guess)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        status["failure"].add(guess)


def check_guesses(volume_path, mount_path, status_file_path, guesses):
    status = load_status(status_file_path, volume_path)

    for guess in guesses:
        if guess in status["failure"]:
            print("skipping '{}' - already attempted".format(guess))
            continue

        make_guess(volume_path, mount_path, status, guess)
        dump_status(status_file_path, status)

        if status["success"]:
            return

    print("guesses exhausted")
    exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("volume_path")
    parser.add_argument("mount_path")
    parser.add_argument("status_file_path")
    args = parser.parse_args()
    check_guesses(
        args.volume_path,
        args.mount_path,
        args.status_file_path,
        gen_guess_alpha_numeric(5),
    )
