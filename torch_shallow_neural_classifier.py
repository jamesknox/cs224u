import numpy as np
import torch
import torch.nn as nn
import torch.utils.data
from torch_model_base import TorchModelBase
from utils import progress_bar

__author__ = "Christopher Potts"
__version__ = "CS224u, Stanford, Spring 2019"


class TorchShallowNeuralClassifier(TorchModelBase):
    def __init__(self, **kwargs):
        super(TorchShallowNeuralClassifier, self).__init__(**kwargs)

    def define_graph(self):
        return nn.Sequential(
            nn.Linear(self.input_dim, self.hidden_dim),
            self.hidden_activation,
            nn.Linear(self.hidden_dim, self.n_classes_))

    def fit(self, X, y, **kwargs):
        """Standard `fit` method.

        Parameters
        ----------
        X : np.array
        y : array-like
        kwargs : dict
            For passing other parameters. If 'X_dev' is included,
            then performance is monitored every 10 epochs; use
            `dev_iter` to control this number.

        Returns
        -------
        self

        """
        # Incremental performance:
        X_dev = kwargs.get('X_dev')
        if X_dev is not None:
            dev_iter = kwargs.get('dev_iter', 10)
        # Data prep:
        X = np.array(X)
        self.input_dim = X.shape[1]
        self.classes_ = sorted(set(y))
        self.n_classes_ = len(self.classes_)
        class2index = dict(zip(self.classes_, range(self.n_classes_)))
        y = [class2index[label] for label in y]
        # Dataset:
        X = torch.tensor(X, dtype=torch.float)
        y = torch.tensor(y, dtype=torch.long)
        dataset = torch.utils.data.TensorDataset(X, y)
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=self.batch_size, shuffle=True)
        # Graph:
        self.model = self.define_graph()
        self.model.to(self.device)
        # Optimization:
        loss = nn.CrossEntropyLoss()
        optimizer = self.optimizer(
            self.model.parameters(),
            lr=self.eta,
            weight_decay=self.l2_strength)
        # Train:
        for iteration in range(1, self.max_iter+1):
            epoch_error = 0.0
            for X_batch, y_batch in dataloader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                batch_preds = self.model(X_batch)
                err = loss(batch_preds, y_batch)
                epoch_error += err.item()
                optimizer.zero_grad()
                err.backward()
                optimizer.step()
            # Incremental predictions where possible:
            if X_dev is not None and iteration > 0 and iteration % dev_iter == 0:
                self.dev_predictions[iteration] = self.predict(X_dev)
            self.errors.append(epoch_error)
            progress_bar(
                "Finished epoch {} of {}; error is {}".format(
                    iteration, self.max_iter, epoch_error))
        return self

    def predict_proba(self, X):
        with torch.no_grad():
            X = torch.tensor(X, dtype=torch.float).to(self.device)
            preds = self.model(X)
            return torch.softmax(preds, dim=1).cpu().numpy()

    def predict(self, X):
        probs = self.predict_proba(X)
        return [self.classes_[i] for i in probs.argmax(axis=1)]


def simple_example():
    """Assess on the digits dataset."""
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score

    digits = load_digits()
    X = digits.data
    y = digits.target

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.33, random_state=42)

    mod = TorchShallowNeuralClassifier()

    print(mod)

    mod.fit(X_train, y_train)
    predictions = mod.predict(X_test)

    print("\nClassification report:")

    print(classification_report(y_test, predictions))

    return accuracy_score(y_test, predictions)


if __name__ == '__main__':
   simple_example()
