from passlib.context import CryptContext
import sys

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python -m subnet.miner_dashboard.generate_pwd_hash <environment> ; where <environment> is 'testnet' or 'mainnet'")
        sys.exit(1)

    password = sys.argv[1]

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Replace 'your-password' with the password you want to hash
    hashed_password = pwd_context.hash(password)
    print(hashed_password)