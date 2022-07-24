from Crypto.PublicKey import RSA


def generate_key():
    key = RSA.generate(2048)

    with open("res/verifier/key", "wb") as f:
        f.write(key.export_key())

    with open("res/verifier/key.pem", "wb") as f:
        f.write(key.publickey().export_key())


if __name__ == "__main__":
    generate_key()
