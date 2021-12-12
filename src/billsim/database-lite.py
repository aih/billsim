#!/usr/bin/env python3

from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine

sqlite_file_name = "./billsim.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

SessionLocal = sessionmaker(autocommit=False,
                            autoflush=False,
                            expire_on_commit=False,
                            bind=engine)
