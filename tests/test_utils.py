import pandas as pd
import numpy as np
import unittest
import os

import site   # so that dl4seq directory is in path
site.addsitedir(os.path.dirname(os.path.dirname(__file__)) )

from dl4seq.utils import make_model
from dl4seq import Model

examples = 2000
ins = 5
outs = 1
in_cols = ['input_'+str(i) for i in range(5)]
out_cols = ['output']
cols=  in_cols + out_cols

data = pd.DataFrame(np.arange(int(examples*len(cols))).reshape(-1,examples).transpose(),
                    columns=cols,
                    index=pd.date_range("20110101", periods=examples, freq="D"))

lookback=7
batch_size=16

def get_layers(o=1, forecast_len=1):

    return {
            "LSTM": {"config": {"units": 1}},
            "Dense": {"config": {"units": o*forecast_len }},
            "Reshape": {"config": {"target_shape": (o, forecast_len)}}
        }


def build_model(**kwargs):

    data_config, nn_config, _ = make_model(
        batch_size=batch_size,
        lookback=lookback,
        normalize=False,
        epochs=1,
        **kwargs
    )

    model = Model(data_config,
                  nn_config,
                  data=data,
                  verbosity=0
                  )

    model.build_nn()

    return model


def train_predict(model):

    x, y = model.train_data(st=10, en=500)

    model.train_nn()
    model.predict()

    return x,y


class TestUtils(unittest.TestCase):

    """
    Given following sample consisting of input/output paris
    input, input, output1, output2, output 3
    1,     11,     21,       31,     41
    2,     12,     22,       32,     42
    3,     13,     23,       33,     43
    4,     14,     24,       34,     44
    5,     15,     25,       35,     45
    6,     16,     26,       36,     46
    7,     17,     27,       37,     47

    if we predict
    27, 37, 47     outs=3, forecast_length=1,  horizon/forecast_step=0,

    if we predict
    28, 38, 48     outs=3, forecast_length=1,  horizon/forecast_step=1,

    if we predict
    27, 37, 47
    28, 38, 48     outs=3, forecast_length=2,  horizon/forecast_step=0,

    if we predict
    28, 38, 48
    29, 39, 49   outs=3, forecast_length=3,  horizon/forecast_step=1,
    30, 40, 50

    if we predict
    38            outs=1, forecast_length=3, forecast_step=0
    39
    40

    if we predict
    39            outs=1, forecast_length=1, forecast_step=2

    if we predict
    39            outs=1, forecast_length=3, forecast_step=2
    40
    41

    output/target/label shape
    (examples, outs, forecast_length)

    Additonally I also build, train and predict from the model so that it is confirmed that everything works
    with different input/output shapes.
    """

    def test_ForecastStep0_Outs(self):
        # test x, y output is fom t not t+1 and number of outputs are 1
        # forecast_length = 1 i.e we are predicting one horizon
        model = build_model(
            inputs = in_cols,
            outputs= out_cols,
            layers=get_layers()
        )

        x, y = train_predict(model)

        self.assertEqual(int(x[0][0].sum()), 140455,)
        self.assertEqual(int(y[0]), 10016)
        self.assertEqual(model.outs, 1)
        self.assertEqual(model.forecast_step, 0)
        return

    def test_ForecastStep0_Outs5(self):
        # test x, y when output is fom t not t+1 and number of inputs are 1 and outputs > 1
        # forecast_length = 1 i.e we are predicting one horizon
        model = build_model(
            inputs = ['input_0'],
            outputs= ['input_1', 'input_2',  'input_3', 'input_4', 'output'],
            layers=get_layers(5)
        )

        x, y = train_predict(model)

        self.assertEqual(model.outs, 5)
        self.assertEqual(model.ins, 1)
        self.assertEqual(model.forecast_step, 0)

        self.assertEqual(int(x[0][0].sum()), 91)
        self.assertEqual(int(y[0].sum()), 30080)
        return

    def test_ForecastStep1_Outs1(self):
        # when we want to predict t+1 given number of outputs are 1
        # forecast_length = 1 i.e we are predicting one horizon

        model = build_model(
            inputs = ['input_0', 'input_1', 'input_2',  'input_3', 'input_4'],
            outputs= ['output'],
            forecast_step=1,
            layers=get_layers()
        )

        x, y = train_predict(model)

        self.assertEqual(model.outs, 1)
        self.assertEqual(model.forecast_step, 1)
        self.assertEqual(int(x[0][-1].sum()), 157325)
        self.assertEqual(int(y[-1].sum()), 10499)
        return

    def test_ForecastStep10_Outs1(self):
        # when we want to predict value t+10 given number of outputs are 1
        # forecast_length = 1 i.e we are predicting one horizon

        model = build_model(
            inputs = in_cols,
            outputs= out_cols,
            forecast_step=10,
            layers={
            "LSTM": {"config": {"units": 1}},
            "Dense": {"config": {"units": 1}},
            "Reshape": {"config": {"target_shape": (1, 1)}}
        }
        )

        x, y = train_predict(model)

        self.assertEqual(model.forecast_step, 10)
        self.assertEqual(int(x[0][-1].sum()), 157010)
        self.assertEqual(int(y[-1].sum()), 10499)
        self.assertEqual(int(x[0][0].sum()), 140455)
        self.assertEqual(int(y[0].sum()), 10026)
        return


    def test_ForecastStep10_Outs5(self):
        # when we want to predict t+10 given number of inputs are 1 and outputs are > 1
        # forecast_length = 1 i.e we are predicting one horizon
        model = build_model(
            inputs = ['input_0'],
            outputs= ['input_1', 'input_2',  'input_3', 'input_4', 'output'],
            forecast_step=10,
            layers=get_layers(5)
        )

        x, y = train_predict(model)

        self.assertEqual(model.forecast_step, 10)
        self.assertEqual(model.outs, 5)
        self.assertEqual(int(x[0][-1].sum()), 3402)
        self.assertEqual(int(y[-1].sum()), 32495)
        self.assertEqual(int(x[0][0].sum()), 91)
        self.assertEqual(int(y[0].sum()), 30130)
        return

    def test_ForecastStep2_Outs1_ForecastLen3(self):
        """
        39
        34
        31
        """
        model = build_model(
            inputs = in_cols,
            outputs= out_cols,
            forecast_step=2,
            forecast_length = 3,
            layers=get_layers(1, 3)
        )


        x, y = train_predict(model)

        self.assertEqual(model.outs, 1)
        self.assertEqual(model.forecast_step, 2)
        self.assertEqual(model.forecast_len, 3)
        self.assertEqual(int(x[0][-1].sum()), 157220)
        self.assertEqual(int(y[-1].sum()), 31494)
        self.assertEqual(int(x[0][0].sum()), 140455)
        self.assertEqual(int(y[0].sum()), 30057)
        self.assertEqual(y[0].shape, (1, 3))
        return

    def test_ForecastStep1_Outs3_ForecastLen3(self):
        """
        we predict
        28, 38, 48
        29, 39, 49   outs=3, forecast_length=3,  horizon/forecast_step=1,
        30, 40, 50
        """

        model = build_model(
            inputs = ['input_0', 'input_1', 'input_2'],
            outputs= ['input_3', 'input_4', 'output'],
            forecast_step=1,
            forecast_length = 3,
            layers=get_layers(3,3)
        )


        x, y = train_predict(model)

        self.assertEqual(model.outs, 3)
        self.assertEqual(model.forecast_step, 1)
        self.assertEqual(model.forecast_len, 3)
        self.assertEqual(int(x[0][-1].sum()), 52353)
        self.assertEqual(int(y[-1].sum()), 76482)
        self.assertEqual(int(x[0][0].sum()), 42273)
        self.assertEqual(int(y[0].sum()), 72162)
        return

    def test_InputStep3(self):
        """
        input_step: 3
        outs = 3
        forecast_step = 2
        forecast_length = 3
        """
        model = build_model(
            inputs = ['input_0', 'input_1', 'input_2'],
            outputs= ['input_3', 'input_4', 'output'],
            forecast_step=2,
            forecast_length = 3,
            input_step=3,
            layers=get_layers(3,3)
        )

        x, y = train_predict(model)

        self.assertEqual(int(x[0][0].sum()), 42399)
        self.assertEqual(int(y[0].sum()), 72279)
        self.assertEqual(int(x[0][-1].sum()), 52164)
        self.assertEqual(int(y[-1].sum()), 76464)
        return

    def test_HighDim(self):
        """
        input_step: 10
        outs = 3
        forecast_step = 10
        forecast_length = 10
        """
        model = build_model(
            inputs = ['input_0', 'input_1', 'input_2'],
            outputs= ['input_3', 'input_4', 'output'],
            forecast_step=10,
            forecast_length = 10,
            input_step=10,
            layers=get_layers(3,10)
        )

        x,y = train_predict(model)

        self.assertEqual(int(x[0][0].sum()), 42840)
        self.assertEqual(int(y[0].sum()), 242535)
        self.assertEqual(int(x[0][-1].sum()), 51261)
        self.assertEqual(int(y[-1].sum()), 254565)
        return

    def test_indexification(self):
        """makes sure that using inexification the order of input/output is reconstructed."""
        model = build_model(
            inputs=in_cols,
            outputs=out_cols,
            layers=get_layers()
        )

        model.get_indices(indices='random')

        test_inputs, true_outputs = model.test_data(indices=model.test_indices,
                                              use_datetime_index=True)


        first_input, inputs, dt_index = model.deindexify_input_data(test_inputs,
                                                                    sort=False,
                                                                    use_datetime_index=True)

        self.assertEqual(dt_index.__class__.__name__, "DatetimeIndex")

        x = test_inputs[0][:, -1, :]
        y = true_outputs[:, :, 0]
        df = pd.DataFrame(np.concatenate([x, y], axis=1), index=dt_index,
                          columns=model.in_cols + model.out_cols).sort_index()

        self.assertEqual(df.shape[0], len(model.test_indices))

        # instead of checking for individual values, we jsut make sure that inputs and outputs are sorted.
        # This is because above we used "random"
        prev_i = 0
        prev_o = 0
        for i,o in zip(df['input_0'][0:10], df['output'][0:10]):
            current_i = i
            current_o = o
            self.assertGreater(current_i, prev_i)
            self.assertGreater(current_o, prev_o)
            prev_i = current_i
            prev_o = current_o

        return

    def test_indexification_with_NaNLabels(self):

        model = build_model(
            inputs=in_cols,
            outputs=out_cols,
            layers=get_layers()
        )

        model.get_indices(indices='random')

        prev_tr_indices = len(model.train_indices)
        prev_test_indices = len(model.test_indices)

        df = data.copy()
        df['output'][100:200] = np.nan

        model.intervals = ((0, 100), (200, 2000))
        model.data = df

        model.build_nn()

        model.get_indices(indices='random')

        self.assertGreater(prev_tr_indices, len(model.train_indices))
        self.assertGreater(prev_test_indices, len(model.test_indices))

        test_inputs, true_outputs = model.test_data(indices=model.test_indices,
                                              use_datetime_index=True)

        _, _, dt_index = model.deindexify_input_data(test_inputs,
                                                     sort=False,
                                                     use_datetime_index=True)

        x = test_inputs[0][:, -1, :]
        y = true_outputs[:, :, 0]
        df = pd.DataFrame(np.concatenate([x, y], axis=1), index=dt_index,
                          columns=model.in_cols + model.out_cols).sort_index()

        # the data for this period must be missing because it had Nans
        self.assertEqual(len(df["20110411": "20110719"]), 0)
        # instead of checking for individual values, we jsut make sure that inputs and outputs are sorted.
        # This is because above we used "random"
        prev_i = 0
        prev_o = 0
        for i,o in zip(df['input_0'][0:10], df['output'][0:10]):
            current_i = i
            current_o = o
            self.assertGreater(current_i, prev_i)
            self.assertGreater(current_o, prev_o)
            prev_i = current_i
            prev_o = current_o

        model.intervals = None
        model.data = data

        return

if __name__ == "__main__":
    unittest.main()