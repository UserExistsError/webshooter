import { nodeResolve } from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import json from '@rollup/plugin-json';

export default {
    input: 'screen/capture_service.js',
    output: {
        file: 'screen/capture_service_bundle.js',
        format: 'cjs',
        exports: 'default'
    },
    plugins: [
        nodeResolve({
            preferBuiltins: true
        }),
        commonjs({
            // This is a hack that keeps the require() from being lifted up top and immediately failing
            ignore: (id) => id === 'string_decoder/'
        }),
        json()
    ]
};