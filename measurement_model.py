"""Snapshot and display geometry for an Overview measurement (no UI/network)."""
from dataclasses import dataclass
from datetime import datetime
import math

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
    extent = max(1.0, abs(value))
    if kind == 'level':
        return value - extent, value + extent
    return (min(0.0, value * 1.25), max(1.0, value * 1.25))


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
