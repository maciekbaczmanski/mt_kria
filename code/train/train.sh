# Copyright 2019 Xilinx Inc.
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

# PART OF THIS FILE AT ALL TIMES.

DET_ROOT=../../data/multi_task_det5_seg16/detection
SEG_ROOT=../../data/multi_task_det5_seg16/segmentation
LANE_ROOT=../../data/multi_task_det5_seg16/lane
DRIVABLE_ROOT=../../data/multi_task_det5_seg16/drivable
SAVE_FOLDER=../../float6
LOAD_FROM=../../float5/iter_44000.pth


echo "Conducting train..."
# python train.py --save_folder "${SAVE_FOLDER}" --batch_size 5 --DET_ROOT ${DET_ROOT} --finetune --SEG_ROOT ${SEG_ROOT} --LANE_ROOT ${LANE_ROOT} --DRIVABLE_ROOT ${DRIVABLE_ROOT} --load_from ${LOAD_FROM}"$@"
# python train.py --save_folder "${SAVE_FOLDER}" --batch_size 5 --DET_ROOT ${DET_ROOT} --finetune --SEG_ROOT ${SEG_ROOT} --LANE_ROOT ${LANE_ROOT} --DRIVABLE_ROOT ${DRIVABLE_ROOT} --start_iter 44000 --resume ${LOAD_FROM}"$@"
python train.py --save_folder "${SAVE_FOLDER}" --batch_size 5 --DET_ROOT ${DET_ROOT} --SEG_ROOT ${SEG_ROOT} --LANE_ROOT ${LANE_ROOT} --DRIVABLE_ROOT ${DRIVABLE_ROOT} "$@"
