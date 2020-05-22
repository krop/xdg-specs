# Global Shortcuts Specification

Authors:

- Noah Davis <<noahadvs@gmail.com>>

Version 0.1

2020-05-21

## About

The purpose of this specification is to reduce the amount of situations where an application and a desktop environment or window manager could have conflicting shortcuts. It is currently intended to be small and easy to comply with. In the future, it could have rules and exceptions for specific shortcuts added, but specific shortcuts are merely examples for now.

For the sake of brevity, desktop environment and window manager shortcuts will be called global shortcuts in this specification since they usually have a global scope.

## Required Rules

These are required rules because they are needed for this specification to work. They should be generally easy to comply with.

1. Applications should never use the Meta/Super key.

## Recommended Rules

These are recommended because a global shortcut may need to be an exception to the rule.

1. Global shortcuts should use the Meta/Super key.
    - Examples:
        - Many creative workflow apps use Alt + Left Click for certain actions. However, global shortcuts for moving windows sometimes conflict with those actions. Instead of Alt + Left Click, those global shortcuts should use Meta/Super + Left Click.
    - Examples of possible exceptions:
        - Many users expect Alt + Tab to switch windows. Most applications already avoid using Alt + Tab for compatibility with existing global shortcuts and cross platform compatibility.
