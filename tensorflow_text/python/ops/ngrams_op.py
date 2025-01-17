# coding=utf-8
# Copyright 2019 TF.Text Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tensorflow ngram operations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import enum

from tensorflow.python.framework import errors
from tensorflow.python.framework import ops
from tensorflow.python.ops import math_ops
from tensorflow.python.ops import string_ops
from tensorflow.python.ops.ragged import ragged_functional_ops
from tensorflow.python.ops.ragged import ragged_tensor
from tensorflow_text.python.ops.sliding_window_op import sliding_window


class Reduction(enum.Enum):
  """Type of reduction to be done by the ngram op.

  The supported reductions are as follows:

  * `Reduction.SUM`: Add values in the window.
  * `Reduction.MEAN`: Average values in the window.
  * `Reduction.STRING_JOIN`: Join strings in the window.
  """

  SUM = 1
  MEAN = 2
  STRING_JOIN = 3


def ngrams(data,
           width,
           axis=-1,
           reduction_type=None,
           string_separator=" ",
           name=None):
  """Create a tensor of n-grams based on the input data `data`.

  Creates a tensor of n-grams based on `data`. The n-grams are of width `width`
  and are created along axis `axis`; the n-grams are created by combining
  windows of `width` adjacent elements from `data` using `reduction_type`. This
  op is intended to cover basic use cases; more complex combinations can be
  created using the sliding_window op.

  Args:
    data: The data to reduce.
    width: The width of the ngram window. If there is not sufficient data to
      fill out the ngram window, the resulting ngram will be empty.
    axis: The axis to create ngrams along. Note that for string join reductions,
      only axis '-1' is supported; for other reductions, any positive or
      negative axis can be used. Should be a constant.
    reduction_type: A member of the Reduction enum. Should be a constant.
      Currently supports:

      * `Reduction.SUM`: Add values in the window.
      * `Reduction.MEAN`: Average values in the window.
      * `Reduction.STRING_JOIN`: Join strings in the window.
        Note that axis must be -1 here.

    string_separator: The separator string used for `Reduction.STRING_JOIN`.
      Ignored otherwise. Must be a string constant, not a Tensor.
    name: The op name.

  Returns:
    A tensor of ngrams.

  Raises:
    InvalidArgumentError: if `reduction_type` is either None or not a Reduction,
      or if `reduction_type` is STRING_JOIN and `axis` is not -1.
  """

  with ops.name_scope(name, "NGrams", [data, width]):
    if reduction_type is None:
      raise errors.InvalidArgumentError(None, None,
                                        "reduction_type must be specified.")

    if not isinstance(reduction_type, Reduction):
      raise errors.InvalidArgumentError(None, None,
                                        "reduction_type must be a Reduction.")

    # TODO(b/122967921): Lift this restriction after ragged_reduce_join is done.
    if reduction_type is Reduction.STRING_JOIN and axis != -1:
      raise errors.InvalidArgumentError(
          None, None, "%s requires that ngrams' 'axis' parameter be -1." %
          Reduction.STRING_JOIN.name)

    windowed_data = sliding_window(data, width, axis)

    if axis < 0:
      reduction_axis = axis
    else:
      reduction_axis = axis + 1

    # Ragged reduction ops work on both Tensor and RaggedTensor, so we can
    # use them here regardless of the type of tensor in 'windowed_data'.
    if reduction_type is Reduction.SUM:
      return math_ops.reduce_sum(windowed_data, reduction_axis)
    elif reduction_type is Reduction.MEAN:
      return math_ops.reduce_mean(windowed_data, reduction_axis)
    elif reduction_type is Reduction.STRING_JOIN:
      if isinstance(data, ragged_tensor.RaggedTensor):
        return ragged_functional_ops.map_flat_values(
            string_ops.reduce_join,
            windowed_data,
            axis=axis,
            separator=string_separator)
      else:
        return string_ops.reduce_join(
            windowed_data, axis=axis, separator=string_separator)
