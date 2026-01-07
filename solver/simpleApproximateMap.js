class SimpleApproximateMap {
  constructor() {
    this.map = new Map();
    this.epoch = 0;
  }

  clear() {
    this.map.clear();
    this.epoch += 1;
  }

  nextEpoch() {
    this.epoch += 1;
  }

  insert(key, value) {
    this.map.set(key, { value, epoch: this.epoch });
  }

  get(key) {
    return this.map.get(key);
  }
}

module.exports = { SimpleApproximateMap };
