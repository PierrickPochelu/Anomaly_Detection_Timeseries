import sys
import numpy as np
import librosa
import librosa.core
import librosa.feature
from strat_map import feature_extractor_strat_map
from read_data.dcase2021_task2_baseline_ae import common as com
# Some comes have been used: https://github.com/y-kawagu/dcase2021_task2_baseline_ae/
"""
def file_load(wav_name, mono=True):
    try:
        x,sampling_rate=librosa.load(wav_name, sr=None, mono=mono)
        return x,sampling_rate
    except Exception as e:
        print(f"Warning in file_load(): cannot read : {wav_name} error={e}")
"""
import os
import glob
from functools import partial
from typing import *

from read_data.normalize_data import normalize
def from_one_file_to_frames(fname, nb_frames, data_prep_info):
    raw_data,sampling_rate=com.file_load(fname)

    # compute frame positions
    frame_size=data_prep_info["frame_size"]
    nb_samples=len(raw_data)
    nb_offsets=frame_size+nb_frames-1
    assert((nb_offsets)<=nb_samples)
    offsets=np.random.choice(range(nb_offsets),nb_frames)

    # compute frames
    frames=[]
    for start_id in offsets:
        raw_frame=raw_data[start_id:start_id+frame_size]
        frames.append(raw_frame)
    return frames


def get_independant_timeserie_names(path):
    # load base_directory list
    query = os.path.abspath(f"{path}/*")
    dirs = sorted(glob.glob(query))
    dir_names = [f for f in dirs if os.path.isdir(f)] # the dir name is also the independant timeserie name

    dir_paths=[]
    for dir_name in dir_names:
        dir_path=os.path.basename(dir_name)
        dir_paths.append( dir_path )

    assert(len(dir_paths)==len(dir_paths))
    return dir_paths, dir_names

def read_and_prepare_one_DCASE_dataset(dataset_name, dataset_path, dataset_prep_info,
                                       nb_frames_per_file=2,
                                       max_files=100):
    # GET RAW SOUND SAMPLES
    assert(os.path.exists(dataset_path))
    x_files_train, y_train = com.file_list_generator(
        DCASE_path=dataset_path,
        dataset_name=dataset_name,
        split_name="train")

    x_files_test, y_test = com.file_list_generator(
        DCASE_path=dataset_path,
        dataset_name=dataset_name,
        split_name="target_test")

    # CREATE THE RAW DATASET
    train_dataset={"x":[], "y":[]}
    test_dataset={"x":[], "y":[]}


    for idx,(fpath,flabel) in enumerate(zip(x_files_train,y_train)):
        print("fpath,flabel->",fpath,flabel)
        file_frames_raw_data=from_one_file_to_frames(fpath,
                                                     nb_frames=nb_frames_per_file,
                                                     data_prep_info=dataset_prep_info)
        file_frames_labels = np.ones((len(file_frames_raw_data),)) * flabel
        train_dataset["x"].append(file_frames_raw_data)
        train_dataset["y"].append(file_frames_labels)
        if idx==max_files:
            break
    for idx,(fpath,flabel) in enumerate(zip(x_files_test,y_test)):
        file_frames_raw_data=from_one_file_to_frames(fpath,
                                                     nb_frames=nb_frames_per_file,
                                                     data_prep_info=dataset_prep_info)
        file_frames_labels = np.ones((len(file_frames_raw_data),)) * flabel
        test_dataset["x"].append(file_frames_raw_data)
        test_dataset["y"].append(file_frames_labels)
        if idx==max_files:
            break

    assert(len(train_dataset["x"])==len(train_dataset["y"]))
    assert(len(test_dataset["x"])==len(test_dataset["y"]))
    train_dataset["x"]=np.concatenate(train_dataset["x"],axis=0)
    train_dataset["y"]=np.concatenate(train_dataset["y"],axis=0)
    test_dataset["x"]=np.concatenate(test_dataset["x"],axis=0)
    test_dataset["y"]=np.concatenate(test_dataset["y"],axis=0)


    assert(len(test_dataset["x"])==len(test_dataset["y"]))


    # NORM THE SIGNAL (TODO: factorization with NAB method is possible
    mean_x_train=np.mean(train_dataset["x"])
    std_x_train=np.std(train_dataset["x"])
    train_dataset["x"]=(train_dataset["x"]-mean_x_train)/(std_x_train+1e-7)
    test_dataset["x"]=(test_dataset["x"]-mean_x_train)/(std_x_train+1e-7)

    # APPLY FEATURE EXTRACTION (TODO: factorization witn NAB method is possible)
    """
    frame_size=dataset_prep_info["frame_size"]
    FE_name=dataset_prep_info["FE_name"]
    FE_hyperparameters=dataset_prep_info.get("FE_hp",None)
    features_extractor=feature_extractor_strat_map[FE_name]
    if FE_hyperparameters is None:
        train_dataset, test_dataset = features_extractor(train_dataset=train_dataset["x"],
                                                         test_dataset=test_dataset["x"],
                                                         frame_size=frame_size)
    else:
        train_dataset, test_dataset = features_extractor(train_dataset=train_dataset["x"],
                                                         test_dataset=test_dataset["x"],
                                                         frame_size=frame_size,
                                                         hyperparameters=FE_hyperparameters)
    """
    # CHECK THE DATASET
    from read_data.read_NAB import check_dataset
    if not check_dataset(train_dataset, test_dataset):
        return None, None
    return train_dataset, test_dataset

from read_data.read_NAB import check_dataset
def DCASE_datasets_generator(path:str, dataset_prep_info:dict):
    dir_paths,dir_names=get_independant_timeserie_names(path)#remember dir_name==dataset_name

    def gen():
        assert(len(dir_paths)==len(dir_names))
        fe = feature_extractor_strat_map[dataset_prep_info["FE_name"]]
        frame_size=dataset_prep_info["frame_size"]
        fe_hp=dataset_prep_info.get("FE_hp",None)

        for dataset_name,dataset_path in zip(dir_paths,dir_names):
            train_dataset,test_dataset=read_and_prepare_one_DCASE_dataset(dataset_name,
                                                                          dataset_path,
                                                                          dataset_prep_info,
                                                                          nb_frames_per_file=2,
                                                                          max_files=100) #read and standardize
            are_valid=check_dataset(train_dataset,test_dataset)
            if are_valid:
                if fe_hp is None:
                    train_dataset, test_dataset = fe(train_dataset, test_dataset, frame_size)
                else:
                    train_dataset,test_dataset=fe(train_dataset,test_dataset,frame_size,fe_hp)

                yield train_dataset, test_dataset
            else:
                pass #
    return gen()


if __name__=="__main__":
    dataset_generator=DCASE_datasets_generator("../data/DCASE/", {"frame_size": 128, "FE_name": "FRAMED", "FE_hp": None})
    for train_dataset,test_dataset in dataset_generator:
        print("train mediane:", np.median(train_dataset["x"]))
        print("test_mediane: ", np.median(test_dataset["x"]))