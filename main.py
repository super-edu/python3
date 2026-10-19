"""Учебный пример конкурентного ожидания в FastAPI."""

import asyncio
import math
from time import perf_counter
from typing import Annotated, Self

from fastapi import FastAPI
from pydantic import BaseModel, Field, FiniteFloat, model_validator


Delay = Annotated[FiniteFloat, Field(ge=0)]


class CalculateRequest(BaseModel):
    numbers: list[FiniteFloat]
    delays: list[Delay]

    @model_validator(mode="after")
    def validate_lists(self) -> Self:
        if len(self.numbers) != len(self.delays):
            raise ValueError("numbers и delays должны иметь одинаковую длину")
        if any(not math.isfinite(number * number) for number in self.numbers):
            raise ValueError("Квадраты чисел должны быть конечными")
        return self


class CalculationResult(BaseModel):
    number: FiniteFloat
    square: FiniteFloat
    delay: Delay
    time: float


class CalculateResponse(BaseModel):
    results: list[CalculationResult]
    total_time: float
    parallel_faster_than_sequential: bool


app = FastAPI(title="Асинхронное вычисление квадратов")


async def calculate_square(number: float, delay: float) -> CalculationResult:
    start = perf_counter()
    # Пока эта задача ждёт, цикл событий выполняет другие задачи.
    await asyncio.sleep(delay)
    square = number * number
    return CalculationResult(
        number=number, square=square, delay=delay, time=perf_counter() - start,
    )


@app.post("/calculate/", response_model=CalculateResponse)
async def calculate(request: CalculateRequest) -> CalculateResponse:
    start = perf_counter()
    # gather запускает корутины конкурентно, сохраняя входной порядок.
    results = await asyncio.gather(*(
        calculate_square(number, delay)
        for number, delay in zip(request.numbers, request.delays)
    ))
    total_time = perf_counter() - start
    return CalculateResponse(
        results=list(results),
        total_time=total_time,
        parallel_faster_than_sequential=total_time < sum(request.delays),
    )
