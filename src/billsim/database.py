#!/usr/bin/env python3

from billsim.constants import POSTGRES_HOST, POSTGRES_PASSWORD, POSTGRES_PORT
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine

postgres_url = f"postgresql://postgres:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}"

engine = create_engine(postgres_url, echo=False)

SessionLocal = sessionmaker(autocommit=False,
                            autoflush=False,
                            expire_on_commit=False,
                            bind=engine)

