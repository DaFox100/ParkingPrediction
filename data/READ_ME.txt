This read me details how to set up the models for parking prediction, how to generate new models or how to use ones already generated
1. set python version to 3.12.6 
2. Install requirements 
    Use the following command: pip install -r /path/to/requirements/requirements.txt 
3. Note that the models in the keras_models file are placeholders, if you want good models, you will either need to generate them yourself or download them from this link,
    https://drive.google.com/drive/folders/1M-IWseAn_hjiwQUDIvP4SV1f6R5w-n6T?usp=sharing
    - Here are the hyperparameters for those models:
        Define parameters for long model
        long_seq = 8
        long_future_steps = 128
        long_feature_shape = short_data.shape[1] + extra_long_data

        # Define parameters for short model
        short_seq = 16
        short_future_steps = 16
        short_feature_shape = short_data.shape[1]

        long_garage_models = []
        short_garage_models = []

        # remember the models will not load correctly if you changes this and don't re-train
        for garage_no, garage in enumerate(garage_names,start=0):
        # long model hyperparameters 
            long_garage_models.append(build_model(
            lstm_neurons_list=[192,32,192],
            dropout=0.1,
            learning_rate=2e-5,
            seq_size=long_seq,
            activation='linear',
            n_feature=long_feature_shape,
            future_steps=long_future_steps,
            garage_no=garage_no))

        # short model hyperparameters 
            short_garage_models.append(build_model(
            lstm_neurons_list=[64,16,64],
            dropout=0.1,
            learning_rate=1e-4,
            seq_size=short_seq,
            activation='celu',
            n_feature=short_feature_shape,
            future_steps=short_future_steps,
            garage_no=garage_no))
            
4. If you want to train your own models for predict_future_times_individual_garage, here are some pointers on where to start,
    - Firstly, make sure that you have the training masks correct:
    # control flags 
        long_training_mask      = [True,True,True,True]
        short_training_mask     = [True,True,True,True]
    The model will only train the garages where the mask is set to true, currently you cannot give different garages different hyperparameters


5. If you want to train your own models for predict_future_times_, here are some pointers on where to start,
    - Unlike the previous version there are only two toggles for training 
        enable_train_short = True
        enable_train_long = True