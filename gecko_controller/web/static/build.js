const path = require('path');
const fs = require('fs');

// Ensure dist directory exists
const distDir = path.join(__dirname, 'dist');
if (!fs.existsSync(distDir)) {
    fs.mkdirSync(distDir, { recursive: true });
}

// Import esbuild using require.resolve to ensure we find it
const esbuildPath = require.resolve('esbuild', { paths: [__dirname, path.join(__dirname, 'node_modules')] });
const esbuild = require(esbuildPath);

const options = {
    entryPoints: ['app.js'],
    bundle: true,
    outfile: 'dist/bundle.js',
    format: 'esm',
        platform: 'browser',
        jsx: 'automatic',
        loader: { '.js': 'jsx' },
        minify: process.env.NODE_ENV === 'production',
        sourcemap: process.env.NODE_ENV !== 'production',
        define: {
            'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development')
        }
};

// Check if watch flag is present
if (process.argv.includes('--watch')) {
    // Start watch mode
    esbuild.context(options).then(ctx => {
        ctx.watch();
        console.log('Watching for changes...');
    });
} else {
    // Single build
    esbuild.build(options).catch(() => process.exit(1));
}
