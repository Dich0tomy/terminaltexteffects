import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


@argclass(
    name="namedeffect",
    help="effect_description",
    description="effect_description",
    epilog=f"""{argvalidators.EASING_EPILOG}
    """,
)
@dataclass
class EffectConfig(ArgsDataClass):
    color_single: graphics.Color = ArgField(
        cmd_name=["--color-single"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=0,
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the ___.",
    )  # type: ignore[assignment]

    color_list: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--color-list"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=0,
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the ___.",
    )  # type: ignore[assignment]

    final_color: graphics.Color = ArgField(
        cmd_name=["--final-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default="ffffff",
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the final character.",
    )  # type: ignore[assignment]

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=5,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=1,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the ___.",
    )  # type: ignore[assignment]

    easing: typing.Callable = ArgField(
        cmd_name=["--easing"],
        default=easing.in_out_sine,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return NamedEffect


class NamedEffectIterator(BaseEffectIterator[EffectConfig]):
    def __init__(self, effect: "NamedEffect") -> None:
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _build(self) -> None:
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self._terminal.output_area.top
            )

            # do something with the data if needed (sort, adjust positions, etc)

    def __next__(self) -> str:
        if self._pending_chars or self._active_chars:
            # perform effect logic
            for character in self._active_chars:
                character.tick()
            return self._terminal.get_formatted_output_string()
        else:
            raise StopIteration


class NamedEffect(BaseEffect[EffectConfig]):
    """Effect description."""

    _config_cls = EffectConfig
    _iterator_cls = NamedEffectIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
