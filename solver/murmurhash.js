// murmurhash.js

function murmurhash64(key) {
	const m = 0xc6a4a7935bd1e995n;
	const r = 47n;
	const seed = 1203989050n;

	const data = Buffer.from(key);
	let h = seed ^ (BigInt(data.length) * m);

	const nblocks = Math.floor(data.length / 8);

	for (let i = 0; i < nblocks; i++) {
		let k = BigInt(data.readBigUInt64LE(i * 8));
		k *= m;
		k ^= k >> r;
		k *= m;
		h ^= k;
		h *= m;
	}

	// Tail
	let k = 0n;
	for (let i = nblocks * 8; i < data.length; i++) {
		k |= BigInt(data[i]) << BigInt((i - nblocks * 8) * 8);
	}

	if (k !== 0n) {
		k *= m;
		k ^= k >> r;
		k *= m;
		h ^= k;
		h *= m;
	}

	h ^= h >> r;
	h *= m;
	h ^= h >> r;

	return h & 0xffffffffffffffffn; // 64-bit unsigned
}

module.exports = { murmurhash64 };
