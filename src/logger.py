from collections import defaultdict
from torch.utils.tensorboard import SummaryWriter
from numbers import Number
from utils import recur


class Logger():
    def __init__(self, log_path):
        self.log_path = log_path
        self.writer = None
        self.tracker = defaultdict(int)
        self.counter = defaultdict(int)
        self.mean = defaultdict(int)
        self.history = defaultdict(list)
        self.iterator = defaultdict(int)

    def safe(self, write):
        if write:
            self.writer = SummaryWriter(self.log_path)
        else:
            if self.writer is not None:
                self.writer.close()
                self.writer = None
        return

    def reset(self):
        self.tracker = defaultdict(int)
        self.counter = defaultdict(int)
        self.mean = defaultdict(int)
        for name in self.mean:
            self.history[name].append(self.mean[name])
        return

    def append(self, result, tag, n=1, mean=True):
        for k in result:
            name = '{}/{}'.format(tag, k)
            self.tracker[name] = result[k]
            self.counter[name] += n
            if mean:
                if isinstance(result[k], Number):
                    self.mean[name] = ((self.counter[name] - n) * self.mean[name] + n * result[k]) / self.counter[name]
                elif isinstance(result[k], list):
                    if self.counter[name] == n:
                        self.mean[name] = [0] * len(result[k])
                    for i in range(len(result[k])):
                        self.mean[name][i] = ((self.counter[name] - n) * self.mean[name][i] + n * result[k][i]) / \
                                             self.counter[name]
                else:
                    raise ValueError('Not valid data type')
        return

    def write(self, tag, metric_names):
        names = ['{}/{}'.format(tag, k) for k in metric_names]
        evaluation_info = []
        for name in names:
            tag, k = name.split('/')
            if isinstance(self.mean[name], Number):
                s = self.mean[name]
            elif isinstance(self.mean[name], list):
                s = sum(self.mean[name]) / len(self.mean[name])
            else:
                raise ValueError('Not valid data type')
            evaluation_info.append('{}: {:.4f}'.format(k, s))
            if self.writer is not None:
                self.iterator[name] += 1
                self.writer.add_scalar(name, s, self.iterator[name])
        info_name = '{}/info'.format(tag)
        info = self.tracker[info_name]
        info[2:2] = evaluation_info
        info = '  '.join(info)
        print(info)
        if self.writer is not None:
            self.iterator[info_name] += 1
            self.writer.add_text(info_name, info, self.iterator[info_name])
        return

    def flush(self):
        self.writer.flush()
        return