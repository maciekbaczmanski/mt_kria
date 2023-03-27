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

DATASET=../../data/multi_task_det5_seg16/detection/Waymo_bdd_txt/val/
WEIGHTS=${1}
IMG_LIST=det_val.txt
GT_FILE=${DATASET}/det_gt.txt
SAVE_FOLDER=../../results/
rm -rf "$SAVE_FOLDER"/det/
mkdir -p "$SAVE_FOLDER"/det/
DT_FILE=${SAVE_FOLDER}/det_test_all.txt
TEST_LOG=${SAVE_FOLDER}/det_log.txt

shift

echo "python -W ignore test.py --i_det --save_folder ${SAVE_FOLDER} --trained_model ${WEIGHTS}  --image_root ${DATASET} --image_list ${IMG_LIST} --img_mode 2 --eval --quant_mode float "$@"" >> ${TEST_LOG}
python -W ignore test.py --i_det --save_folder ${SAVE_FOLDER} --trained_model ${WEIGHTS}  --image_root ${DATASET} --image_list ${IMG_LIST} --img_mode 2 --eval --quant_mode float "$@"
cat ${SAVE_FOLDER}/det/* > ${DT_FILE}
python ./evaluation/evaluate_det.py -gt_file ${GT_FILE} -result_file ${DT_FILE} | tee -a ${TEST_LOG}
echo "Test report is saved to ${TEST_LOG}"

rm -rf "$SAVE_FOLDER"/det/
