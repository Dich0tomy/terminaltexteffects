import importlib
import argparse
import terminaltexteffects.effects
import pkgutil
import terminaltexteffects.utils.terminal as term


def main():
    parser = (argparse.ArgumentParser)(
        prog="terminaltexteffects", description="Apply visual effects to terminal text piped in from stdin."
    )
    subparsers = parser.add_subparsers(
        title="Effect",
        description="Name of the effect to apply. Use <effect> -h for effect specific help.",
        help="Available Effects",
        required=True,
    )

    discovered_effects = [
        importlib.import_module(module.name)
        for module in pkgutil.iter_modules(
            terminaltexteffects.effects.__path__, terminaltexteffects.effects.__name__ + "."
        )
    ]

    for effect in discovered_effects:
        effect.add_arguments(subparsers)

    args = parser.parse_args()
    input_data = term.Terminal.get_piped_input()
    if not input_data:
        print("NO INPUT.")
    else:
        terminal = term.Terminal(input_data)
        effect = args.effect_class(terminal, args)
        effect.run()


if __name__ == "__main__":
    main()