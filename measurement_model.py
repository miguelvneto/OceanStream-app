"""Snapshot and display geometry for an Overview measurement (no UI/network)."""
from dataclasses import dataclass
from datetime import datetime
import math
from decimal import Decimal

VISUAL_TYPES = {
    'Maré Reduzida': 'level',
    'Dir. Corr.': 'direction', 'Direção de Corrente': 'direction',
    'Dir. Vento': 'direction', 'Direção de Vento': 'direction',
    'Direção Onda': 'direction',
    'Vel. Corr.': 'speed', 'Velocidade de Corrente': 'speed',
    'Vel. Vento': 'speed', 'Velocidade de Vento': 'speed', 'Rajada': 'speed',
    'Altura Onda': 'wave_height', 'Altura': 'wave_height',
    'Período Onda': 'wave_period', 'Período': 'wave_period',
    'Período Médio': 'wave_period', 'Bateria': 'battery',
    'Pitch': 'pitch', 'Roll': 'roll', 'Chuva': 'rain',
}


def finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


@dataclass(frozen=True)
class Measurement:
    name: str
    value: object
    display_value: str
    unit: str
    icon: str
    origin: str
    timestamp: str

    @property
    def visual_type(self):
        return VISUAL_TYPES.get(self.name, 'generic')

    @property
    def number(self):
        return finite_number(self.value)

    @property
    def renderer(self):
        kind = self.visual_type
        if self.number is None:
            return 'generic'
        return kind


def direction_geometry(value):
    """Clockwise degrees from north, without inferring from/to convention."""
    angle = value % 360
    radians = math.radians(angle)
    cardinal = ('N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO')[int((angle + 22.5) // 45) % 8]
    return math.sin(radians), math.cos(radians), cardinal


def visual_scale(value, kind):
    """Display-only scale, never an operational/safety limit."""
    ticks = scale_ticks(value, kind)
    return ticks[0], ticks[-1]


def nice_number(value):
    """Round a positive magnitude upward to a readable decimal number."""
    if value <= 0 or not math.isfinite(value):
        raise ValueError('Expected a positive finite magnitude')
    power = 10 ** math.floor(math.log10(value))
    for factor in (1, 2, 2.5, 5, 10):
        if value <= factor * power * (1 + 1e-12):
            return float(Decimal(str(factor)) * Decimal(str(power)))


def scale_ticks(value, kind):
    """Regular ticks with readable limits; never physical or charge limits."""
    extent = max(.1, abs(value))
    if kind == 'level':
        step = nice_number(extent / 3)
        first = math.floor((value - extent * .6) / step)
        last = math.ceil((value + extent * .6) / step)
    else:
        step = nice_number(extent * 1.1 / 5)
        intervals = math.ceil(extent * 1.1 / step)
        first, last = (-intervals, 0) if value < 0 else (0, intervals)
    return tuple(float(Decimal(str(step)) * i) for i in range(first, last + 1))


def tick_labels(ticks):
    step = Decimal(str(ticks[1])) - Decimal(str(ticks[0]))
    decimals = max(0, -step.normalize().as_tuple().exponent)
    return tuple(f'{value:.{decimals}f}' for value in ticks)


def indicator_angle(value, progress, compass=False):
    """Animate from level/north, with the shortest path for a compass."""
    target = (value + 180) % 360 - 180 if compass else value
    return target * max(0, min(1, progress))


def inclination_geometry(value, progress=1):
    """Positive is counterclockwise on screen; no inferred physical convention."""
    radians = math.radians(indicator_angle(value, progress))
    return math.cos(radians), math.sin(radians)


def fitted_image_size(native_size, available_size):
    """Preserve aspect ratio and never upscale beyond the source pixels."""
    width, height = native_size
    if width <= 0 or height <= 0:
        return (0, 0)
    ratio = max(0, min(1, available_size[0] / width, available_size[1] / height))
    return width * ratio, height * ratio


def measurement_ticks(measurement):
    if (measurement.renderer == 'battery' and measurement.unit.strip() == '%'
            and 0 <= measurement.number <= 100):
        return (0, 20, 40, 60, 80, 100)
    return scale_ticks(measurement.number, measurement.renderer)


def equipment_snapshot(measurements, selected):
    """Keep display order and isolate one equipment; retain stale tapped data."""
    group = tuple(item for item in measurements if item.origin == selected.origin)
    for index, item in enumerate(group):
        if item is selected:
            return group, index
    if selected in group:
        return group, group.index(selected)
    # A refresh may have replaced cards between touch down and release.
    return (selected,), 0


def friendly_timestamp(value):
    if not value:
        return 'Não informado'
    try:
        return datetime.fromisoformat(value.strip().replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M')
    except (TypeError, ValueError, AttributeError):
        return str(value)
