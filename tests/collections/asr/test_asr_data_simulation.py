# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
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

from typing import List, Type, Union

import numpy as np
import pytest
from numpy.random import default_rng

from nemo.collections.asr.data.data_simulation import (
    ArrayGeometry,
    check_angle,
    convert_placement_to_range,
    convert_rir_to_multichannel,
    wrap_to_180,
)


class TestDataSimulationUtils:
    @pytest.mark.unit
    def test_check_angle(self):
        """Test angle checks.
        """
        num_examples = 100
        random = default_rng()

        assert check_angle('azimuth', random.uniform(low=-180, high=180, size=num_examples)) == True
        assert check_angle('elevation', random.uniform(low=-90, high=90, size=num_examples)) == True
        assert check_angle('yaw', random.uniform(low=-180, high=180, size=num_examples)) == True
        assert check_angle('pitch', random.uniform(low=-90, high=90, size=num_examples)) == True
        assert check_angle('roll', random.uniform(low=-180, high=180, size=num_examples)) == True

        with pytest.raises(ValueError):
            check_angle('azimuth', [-200, 200])

        with pytest.raises(ValueError):
            check_angle('elevation', [-100, 100])

        with pytest.raises(ValueError):
            check_angle('yaw', [-200, 200])

        with pytest.raises(ValueError):
            check_angle('pitch', [-200, 200])

        with pytest.raises(ValueError):
            check_angle('roll', [-200, 200])

    @pytest.mark.unit
    def test_wrap_to_180(self):
        """Test wrap.
        """
        test_cases = []
        test_cases.append({'angle': 0, 'wrapped': 0})
        test_cases.append({'angle': 45, 'wrapped': 45})
        test_cases.append({'angle': -30, 'wrapped': -30})
        test_cases.append({'angle': 179, 'wrapped': 179})
        test_cases.append({'angle': -179, 'wrapped': -179})
        test_cases.append({'angle': 181, 'wrapped': -179})
        test_cases.append({'angle': -181, 'wrapped': 179})
        test_cases.append({'angle': 270, 'wrapped': -90})
        test_cases.append({'angle': -270, 'wrapped': 90})
        test_cases.append({'angle': 359, 'wrapped': -1})
        test_cases.append({'angle': 360, 'wrapped': 0})

        for test_case in test_cases:
            assert wrap_to_180(test_case['angle']) == test_case['wrapped']

    @pytest.mark.unit
    def test_placement_range(self):
        """Test placement range conversion.
        """
        # Setup 1:
        test_cases = []
        test_cases.append(
            {
                'room_dim': [3, 4, 5],
                'placement': {'x': None, 'y': None, 'height': None, 'min_to_wall': 0},
                'object_radius': 0,
                'expected_range': np.array([[0, 3], [0, 4], [0, 5]]),
            }
        )

        test_cases.append(
            {
                'room_dim': [3, 4, 5],
                'placement': {'x': None, 'y': None, 'height': None, 'min_to_wall': 0},
                'object_radius': 0.1,
                'expected_range': np.array([[0.1, 2.9], [0.1, 3.9], [0.1, 4.9]]),
            }
        )

        test_cases.append(
            {
                'room_dim': [3, 4, 5],
                'placement': {'x': None, 'y': None, 'height': None, 'min_to_wall': 0.5},
                'object_radius': 0.1,
                'expected_range': np.array([[0.6, 2.4], [0.6, 3.4], [0.6, 4.4]]),
            }
        )

        test_cases.append(
            {
                'room_dim': [3, 4, 5],
                'placement': {'x': [1, 3], 'y': [0.3, 3.0], 'height': [1.5, 1.8], 'min_to_wall': 0.5},
                'object_radius': 0.1,
                'expected_range': np.array([[1, 2.4], [0.6, 3.0], [1.5, 1.8]]),
            }
        )

        test_cases.append(
            {
                'room_dim': [3, 4, 5],
                'placement': {'x': 2, 'y': 3, 'height': [1.5, 1.8], 'min_to_wall': 0.5},
                'object_radius': 0.1,
                'expected_range': np.array([[2, 2], [3, 3], [1.5, 1.8]]),
            }
        )

        for test_case in test_cases:
            placement_range = convert_placement_to_range(
                test_case['placement'], test_case['room_dim'], test_case['object_radius']
            )

            assert np.all(placement_range == test_case['expected_range'])

        with pytest.raises(ValueError):
            # fail because of negative x
            convert_placement_to_range(
                **{
                    'room_dim': [3, 4, 5],
                    'placement': {'x': -1, 'y': None, 'height': None, 'min_to_wall': 0},
                    'object_radius': 0.1,
                }
            )

        with pytest.raises(ValueError):
            # fail because of negative min_to_wall
            convert_placement_to_range(
                **{
                    'room_dim': [3, 4, 5],
                    'placement': {'x': None, 'y': None, 'height': None, 'min_to_wall': -1},
                    'object_radius': 0.1,
                }
            )

        with pytest.raises(ValueError):
            # fail because height range doesn't have exactly two elements
            convert_placement_to_range(
                **{
                    'room_dim': [3, 4, 5],
                    'placement': {'x': None, 'y': None, 'height': [1], 'min_to_wall': 0},
                    'object_radius': 0.1,
                }
            )

        with pytest.raises(ValueError):
            # fail because the room is too small for constraint
            convert_placement_to_range(
                **{
                    'room_dim': [1, 2, 3],
                    'placement': {'x': None, 'y': None, 'height': None, 'min_to_wall': 1},
                    'object_radius': 0.1,
                }
            )

    @pytest.mark.unit
    @pytest.mark.parametrize("num_mics", [2, 4])
    @pytest.mark.parametrize("num_sources", [1, 3])
    def test_convert_rir_to_mc(self, num_mics: int, num_sources: int):
        """Test conversion of a RIR from list of lists to multichannel array.
        """
        len_range = [50, 1000]
        random = default_rng()

        rir = []
        rir_len = []

        # Golden reference
        for n_mic in range(num_mics):
            this_rir = []
            this_len = []
            for n_source in range(num_sources):
                random_len = np.random.randint(low=len_range[0], high=len_range[1])
                this_rir.append(np.random.rand(random_len))
                this_len.append(random_len)
            rir.append(this_rir)
            rir_len.append(this_len)

        # UUT
        mc_rir = convert_rir_to_multichannel(rir)

        # Compare
        for n_source in range(num_sources):
            for n_mic in range(num_mics):
                # check RIR
                diff_len = rir_len[n_mic][n_source]
                diff = mc_rir[n_source][:diff_len, n_mic] - rir[n_mic][n_source]
                assert np.all(diff == 0.0), f'Original RIR not matching: source={n_source}, channel={n_mic}'

                # check padding
                pad = mc_rir[n_source][diff_len:, n_mic]
                assert np.all(pad == 0.0), f'Original RIR not matching: source={n_source}, channel={n_mic}'


class TestArrayGeometry:
    @pytest.mark.unit
    @pytest.mark.parametrize('mic_spacing', [0.05])
    @pytest.mark.parametrize("num_mics", [2, 4])
    @pytest.mark.parametrize("axis", [0, 1, 2])
    def test_array_geometry(self, mic_spacing: float, num_mics: int, axis: int):
        max_abs_tol = 1e-8
        random = default_rng()

        # assume linear arrray along axis
        mic_positions = np.zeros((num_mics, 3))
        mic_positions[:, axis] = mic_spacing * np.arange(num_mics)

        center = np.mean(mic_positions, axis=0)
        mic_positions_centered = mic_positions - center

        uut = ArrayGeometry(mic_positions)

        # test initialization
        assert np.max(np.abs(uut.center - center)) < max_abs_tol
        assert np.max(np.abs(uut.centered_positions - mic_positions_centered)) < max_abs_tol
        assert np.max(np.abs(uut.positions - mic_positions)) < max_abs_tol

        # test translation
        center = random.uniform(low=-10, high=-10, size=3)
        mic_positions = mic_positions_centered + center
        uut.translate(to=center)

        assert np.max(np.abs(uut.center - center)) < max_abs_tol
        assert np.max(np.abs(uut.centered_positions - mic_positions_centered)) < max_abs_tol
        assert np.max(np.abs(uut.positions - mic_positions)) < max_abs_tol

        # test rotation
        center = uut.center
        centered_positions = uut.centered_positions
        test_cases = []
        test_cases.append(
            {
                'orientation': {'yaw': 90},
                'new_positions': np.vstack(
                    (-centered_positions[:, 1], centered_positions[:, 0], centered_positions[:, 2])
                ).T,
            }
        )

        test_cases.append(
            {
                'orientation': {'pitch': 90},
                'new_positions': np.vstack(
                    (centered_positions[:, 2], centered_positions[:, 1], -centered_positions[:, 0])
                ).T,
            }
        )

        test_cases.append(
            {
                'orientation': {'roll': 90},
                'new_positions': np.vstack(
                    (centered_positions[:, 0], -centered_positions[:, 2], centered_positions[:, 1])
                ).T,
            }
        )

        for test_case in test_cases:
            new_array = uut.new_rotated_array(**test_case['orientation'])
            assert np.max(np.abs(new_array.center - center)) < max_abs_tol
            assert np.max(np.abs(new_array.centered_positions - test_case['new_positions'])) < max_abs_tol

        # test radius
        assert np.max(np.abs(uut.radius - (num_mics - 1) / 2 * mic_spacing)) < max_abs_tol

        # test conversion to spherical
        # point on x axis
        point = np.array([1, 0, 0])

        test_cases = []
        test_cases.append({'center': 0, 'dist': np.linalg.norm(point - 0), 'azim': 0, 'elev': 0})

        test_cases.append(
            {
                'center': np.array([2, 0, 0]),
                'dist': np.linalg.norm(point - np.array([2, 0, 0])),
                'azim': -180,
                'elev': 0,
            }
        )

        test_cases.append(
            {
                'center': np.array([1, 1, 1]),
                'dist': np.linalg.norm(point - np.array([1, 1, 1])),
                'azim': -90,
                'elev': -45,
            }
        )

        test_cases.append(
            {
                'center': np.array([1, 2, -2]),
                'dist': np.linalg.norm(point - np.array([1, 2, -2])),
                'azim': -90,
                'elev': 45,
            }
        )

        for test_case in test_cases:
            uut.translate(to=test_case['center'])
            dist, azim, elev = uut.spherical_relative_to_array(point)
            assert abs(dist - test_case['dist']) < max_abs_tol
            assert abs(wrap_to_180(azim - test_case['azim'])) < max_abs_tol
            assert abs(elev - test_case['elev']) < max_abs_tol
