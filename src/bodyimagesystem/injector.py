"""Small injection helper commonly used by Sims 4 script mods."""

import functools


def inject_to(target_object, target_function_name):
    """Wrap target_object.target_function_name with a function receiving original."""

    def _inject(new_function):
        original_function = getattr(target_object, target_function_name)

        @functools.wraps(original_function)
        def _wrapped(*args, **kwargs):
            return new_function(original_function, *args, **kwargs)

        setattr(target_object, target_function_name, _wrapped)
        return new_function

    return _inject

