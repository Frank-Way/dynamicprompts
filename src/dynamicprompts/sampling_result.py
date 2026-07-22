from __future__ import annotations

import dataclasses
from typing import Iterable

from dynamicprompts.commands import Command
from dynamicprompts.commands.wrap_command import split_wrapper_string


@dataclasses.dataclass(frozen=True)
class SamplingResult:
    """
    An internal result of a sampling. May contain metadata in the future.
    """

    text: str
    variables: dict[str, Command] = dataclasses.field(default_factory=dict)

    def __str__(self):
        return self.text

    @property
    def dedupe_key(self) -> tuple:
        # Used by e.g. combinatorial sampling's fragment deduplication.
        # Please make sure to update this if you add more fields to SamplingResult.
        var_key = tuple(sorted(self.variables.keys()))
        return (self.text, var_key)

    def whitespace_squashed(self) -> SamplingResult:
        from dynamicprompts.utils import squash_whitespace

        return dataclasses.replace(
            self,
            text=squash_whitespace(self.text),
            variables=self.variables,
        )

    def text_replaced(self, new_text: str) -> SamplingResult:
        return dataclasses.replace(self, text=new_text, variables=self.variables)

    def as_wrapper(self):
        """
        Return a function that wraps a SamplingResult with this one,
        partitioning this result's text along the wrap marker.
        """
        prefix, suffix = split_wrapper_string(self.text)
        prefix_res = self.text_replaced(prefix)
        suffix_res = self.text_replaced(suffix)

        def wrapper(inner: SamplingResult) -> SamplingResult:
            return SamplingResult.joined([prefix_res, inner, suffix_res], separator="")

        return wrapper

    @classmethod
    def joined(
        cls,
        results: Iterable[SamplingResult],
        *,
        separator: str,
    ) -> SamplingResult:
        from dynamicprompts.utils import removeprefix, removesuffix

        results_list = list(results)

        if len(results_list) == 1:
            # Special case: when we have a single result,
            # there's no point in joining anything, or doing
            # the special handling to strip separators (since
            # we never added any).  This means that a separator
            # in the input will be preserved; this is intentional.
            return results_list[0]

        joined = separator.join(r.text for r in results_list)

        # Merge variables from all sub-results (later wins)
        merged_variables: dict[str, Command] = {}
        for r in results_list:
            merged_variables.update(r.variables)

        if separator:
            joined = removeprefix(joined, separator)
            joined = removesuffix(joined, separator)
        return cls(text=joined, variables=merged_variables)
