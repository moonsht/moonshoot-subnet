## how to run migrations

https://chatgpt.com/share/66ee7ab2-2fec-800e-a286-5b1e2e387e06


alembic --config src/subnet/miner/alembic.ini upgrade head
alembic --config src/subnet/miner/alembic.ini revision --autogenerate -m "initial" --rev-id 001


alembic --config src/subnet/validator/alembic.ini upgrade head
alembic --config src/subnet/validator/alembic.ini revision --autogenerate -m "initial" --rev-id 001
