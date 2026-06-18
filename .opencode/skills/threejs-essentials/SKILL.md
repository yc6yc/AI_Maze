---
name: threejs-essentials
description: Use when working with Three.js 3D scenes, WebGL rendering, 3D game development, or any Three.js project setup. Covers scene creation, cameras, lighting, geometries, materials, animation loops, model loading, post-processing, and common patterns. Use ONLY when the user needs Three.js-specific guidance.
---

# Three.js Essentials

Reference for common Three.js patterns, best practices, and boilerplate. Based on Three.js r160+ (ES module imports).

## Project Setup

```bash
npm install three
npm install -D @types/three vite
```

### Import Style (ESM)

```ts
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
```

## Minimal Scene

```ts
import * as THREE from 'three';

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111111);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 5, 10);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
document.body.appendChild(renderer.domElement);

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
```

## Cameras

```ts
// Perspective (most common)
const camera = new THREE.PerspectiveCamera(fov, aspect, near, far);
camera.position.set(x, y, z);
camera.lookAt(target);

// Orthographic (2D/isometric)
const frustumSize = 10;
const aspect = window.innerWidth / window.innerHeight;
const camera = new THREE.OrthographicCamera(
  frustumSize * aspect / -2, frustumSize * aspect / 2,
  frustumSize / 2, frustumSize / -2, 0.1, 1000
);
```

## Lighting Patterns

### Standard Three-Point Setup
```ts
const ambient = new THREE.AmbientLight(0x404080, 0.5);
scene.add(ambient);

const sun = new THREE.DirectionalLight(0xffffff, 3);
sun.position.set(50, 50, 50);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.near = 0.5;
sun.shadow.camera.far = 500;
sun.shadow.camera.left = -100;
sun.shadow.camera.right = 100;
sun.shadow.camera.top = 100;
sun.shadow.camera.bottom = -100;
scene.add(sun);

const fill = new THREE.DirectionalLight(0x8888ff, 0.5);
fill.position.set(-30, 10, -20);
scene.add(fill);
```

### Hemisphere (outdoor scenes)
```ts
const hemi = new THREE.HemisphereLight(0xddeeff, 0x0f0e0d, 1);
scene.add(hemi);
```

### Point / Spot lights
```ts
const point = new THREE.PointLight(0xff5500, 50, 20);
point.position.set(0, 3, 0);
point.castShadow = true;
scene.add(point);

const spot = new THREE.SpotLight(0xffffff, 100, 30, Math.PI / 6, 0.3, 1);
spot.position.set(0, 10, 0);
spot.castShadow = true;
spot.target.position.set(0, 0, 0);
scene.add(spot);
scene.add(spot.target);
```

## Geometries Quick Reference

```ts
new THREE.BoxGeometry(w, h, d, segW, segH, segD);
new THREE.SphereGeometry(radius, widthSeg, heightSeg);
new THREE.PlaneGeometry(w, h, segW, segH);
new THREE.CylinderGeometry(topR, bottomR, h, radialSeg, heightSeg, openEnded);
new THREE.ConeGeometry(radius, h, radialSeg, heightSeg);
new THREE.TorusGeometry(radius, tube, radialSeg, tubularSeg);
new THREE.CapsuleGeometry(radius, length, capSeg, radialSeg);
new THREE.RoundedBoxGeometry(w, h, d, segments, radius);  // addon
new THREE.TorusKnotGeometry(radius, tube, tubularSeg, radialSeg, p, q);
new THREE.RingGeometry(innerR, outerR, seg);
new THREE.DodecahedronGeometry(radius);
new THREE.IcosahedronGeometry(radius);
```

### Extrude / Lathe / ShapeGeometry
```ts
const shape = new THREE.Shape();
shape.moveTo(0, 0);
shape.lineTo(1, 0);
shape.lineTo(1, 1);
shape.lineTo(0, 1);
const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.5, bevelEnabled: true, bevelThickness: 0.1, bevelSize: 0.1, bevelSegments: 3 });
```

### BufferGeometry (custom)
```ts
const geo = new THREE.BufferGeometry();
const vertices = new Float32Array([0,0,0, 1,0,0, 0,1,0]);
geo.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
geo.setIndex([0, 1, 2]);
geo.computeVertexNormals();
```

## Materials Quick Reference

| Material | Use Case |
|----------|----------|
| `MeshStandardMaterial` | PBR, default choice |
| `MeshBasicMaterial` | Unlit, emissive-style |
| `MeshPhongMaterial` | Fast, shiny |
| `MeshLambertMaterial` | Matte, diffuse-only |
| `MeshNormalMaterial` | Debug normals |
| `MeshToonMaterial` | Cel-shaded / cartoon |
| `MeshMatcapMaterial` | Cheap baked lighting |
| `MeshDepthMaterial` | Depth / fog effects |
| `MeshPhysicalMaterial` | Clearcoat, transmission, glass |
| `PointsMaterial` | Particle systems |
| `LineBasicMaterial` | Wireframe lines |
| `ShaderMaterial` | Custom GLSL shaders |

### Standard PBR Material
```ts
const mat = new THREE.MeshStandardMaterial({
  color: 0x6688cc,
  roughness: 0.4,
  metalness: 0.2,
  map: textureLoader.load('/textures/diffuse.jpg'),
  normalMap: textureLoader.load('/textures/normal.jpg'),
  roughnessMap: textureLoader.load('/textures/roughness.jpg'),
  aoMap: textureLoader.load('/textures/ao.jpg'),
  envMap: envMap,
  envMapIntensity: 0.5,
});
```

### Physical Material (glass, clearcoat)
```ts
const glass = new THREE.MeshPhysicalMaterial({
  roughness: 0,
  metalness: 0,
  transmission: 1,
  thickness: 0.5,
  ior: 1.5,
  clearcoat: 0.3,
  clearcoatRoughness: 0.25,
  envMapIntensity: 1,
});
```

## Texture Loading

```ts
const loader = new THREE.TextureLoader();
loader.setPath('/textures/');

const diffuse = loader.load('diffuse.jpg');
diffuse.colorSpace = THREE.SRGBColorSpace;
diffuse.wrapS = THREE.RepeatWrapping;
diffuse.wrapT = THREE.RepeatWrapping;
diffuse.repeat.set(2, 2);
```

### Texture color space rules:
- Albedo/color/emissive: `THREE.SRGBColorSpace`
- Normal/roughness/metalness/ao/displacement/alpha: `THREE.LinearSRGBColorSpace`

### CubeTexture / Environment Map
```ts
const cubeLoader = new THREE.CubeTextureLoader();
cubeLoader.setPath('/env/');
const envMap = cubeLoader.load(['px.jpg','nx.jpg','py.jpg','ny.jpg','pz.jpg','nz.jpg']);
scene.background = envMap;
scene.environment = envMap;
```

### HDR Environment (RGBELoader)
```ts
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
const rgbeLoader = new RGBELoader();
rgbeLoader.load('/env.hdr', (texture) => {
  texture.mapping = THREE.EquirectangularReflectionMapping;
  scene.environment = texture;
  scene.background = texture;
  scene.backgroundBlurriness = 0.5;
});
```

### KTX2 (compressed textures)
```ts
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
const ktx2Loader = new KTX2Loader().setTranscoderPath('/basis/').detectSupport(renderer);
const texture = ktx2Loader.load('/texture.ktx2', (t) => { t.colorSpace = THREE.SRGBColorSpace; });
```

## Shadows

```ts
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

// On light:
light.castShadow = true;
light.shadow.mapSize.set(1024, 1024);
light.shadow.bias = -0.0001;
light.shadow.normalBias = 0.02;

// On mesh:
mesh.castShadow = true;
mesh.receiveShadow = true;
```

**Performance tip:** Use `THREE.PCFSoftShadowMap` for quality, `THREE.PCFShadowMap` for speed, `THREE.BasicShadowMap` for mobile.

## Animation Loop (delta-based)

```ts
const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);
  const delta = Math.min(clock.getDelta(), 0.1); // cap delta

  // Update logic using delta...
  mesh.rotation.y += 0.5 * delta;

  renderer.render(scene, camera);
}
```

## Loading 3D Models

### GLTF/GLB (recommended)
```ts
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

const loader = new GLTFLoader();
const dracoLoader = new DRACOLoader();
dracoLoader.setDecoderPath('/draco/');
loader.setDRACOLoader(dracoLoader);

loader.load('/model.glb', (gltf) => {
  const model = gltf.scene;
  model.position.set(0, 0, 0);
  model.scale.set(1, 1, 1);
  model.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });
  scene.add(model);
}, (progress) => {
  console.log(`Loading: ${(progress.loaded / progress.total * 100).toFixed(0)}%`);
}, (error) => {
  console.error('GLTF load error:', error);
});
```

### FBX
```ts
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
new FBXLoader().load('/model.fbx', (fbx) => scene.add(fbx));
```

### OBJ + MTL
```ts
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js';
new MTLLoader().load('/model.mtl', (mtl) => {
  mtl.preload();
  new OBJLoader().setMaterials(mtl).load('/model.obj', (obj) => scene.add(obj));
});
```

## Raycasting / Interaction

```ts
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

window.addEventListener('click', (event) => {
  mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(scene.children, true);

  if (intersects.length > 0) {
    const hit = intersects[0].object;
    hit.material.color.set(0xff0000);
  }
});
```

### With a pointermove throttle:
```ts
let hovered = null;
window.addEventListener('pointermove', (e) => {
  mouse.set((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1);
  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects(interactableObjects);
  if (hits.length > 0) {
    const obj = hits[0].object;
    if (hovered !== obj) {
      if (hovered) hovered.material.emissive.set(0x000000);
      hovered = obj;
      hovered.material.emissive.set(0x222222);
    }
  } else {
    if (hovered) { hovered.material.emissive.set(0x000000); hovered = null; }
  }
});
```

## Post-Processing (EffectComposer)

```ts
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { RGBShiftShader } from 'three/addons/shaders/RGBShiftShader.js';
import { FXAAShader } from 'three/addons/shaders/FXAAShader.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
```

### Composer setup:
```ts
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));

const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight), 1.5, 0.4, 0.85
);
bloomPass.threshold = 0.5;
bloomPass.strength = 1.2;
bloomPass.radius = 0.8;
composer.addPass(bloomPass);

const fxaaPass = new ShaderPass(FXAAShader);
fxaaPass.uniforms['resolution'].value.set(
  1 / (window.innerWidth * renderer.getPixelRatio()),
  1 / (window.innerHeight * renderer.getPixelRatio())
);
composer.addPass(fxaaPass);

composer.addPass(new OutputPass());

// Replace renderer.render with composer.render in animate():
composer.render();
```

### Common post-processing passes:
- `RenderPass` — required base pass
- `UnrealBloomPass` — glow effect
- `ShaderPass(FXAAShader)` — anti-aliasing
- `ShaderPass(RGBShiftShader)` — chromatic aberration
- `GlitchPass` — glitch effect
- `AfterimagePass` — motion trails
- `SSAOPass` — ambient occlusion
- `BokehPass` — depth of field
- `OutputPass` — color space conversion (required for WebGLRenderer output)

## Performance Optimization

```ts
// Frustum culling (on by default, don't disable unless needed)
mesh.frustumCulled = true;

// Object pooling for particles/bullets
const pool: THREE.Mesh[] = [];
function getMesh(): THREE.Mesh {
  return pool.pop() || createNewMesh();
}
function returnMesh(m: THREE.Mesh) { m.visible = false; pool.push(m); }

// Use InstancedMesh for many identical objects
const count = 1000;
const instanced = new THREE.InstancedMesh(geometry, material, count);
const dummy = new THREE.Object3D();
for (let i = 0; i < count; i++) {
  dummy.position.set(Math.random() * 100, 0, Math.random() * 100);
  dummy.updateMatrix();
  instanced.setMatrixAt(i, dummy.matrix);
}
instanced.instanceMatrix.needsUpdate = true;

// Dispose unused resources
function disposeMesh(mesh: THREE.Mesh) {
  mesh.geometry.dispose();
  if (Array.isArray(mesh.material)) {
    mesh.material.forEach(m => disposeMaterial(m));
  } else {
    disposeMaterial(mesh.material);
  }
}
function disposeMaterial(mat: THREE.Material) {
  for (const key of Object.keys(mat)) {
    const value = (mat as any)[key];
    if (value && value.isTexture) value.dispose();
  }
  mat.dispose();
}

// Merge static geometry
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
const merged = mergeGeometries(geometries, false);

// Use lower resolution shadows
light.shadow.mapSize.set(512, 512);

// Limit render resolution
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
```

## Common Patterns

### Object follow camera (third-person)
```ts
const offset = new THREE.Vector3(0, 5, -10);
target.getWorldPosition(worldPos);
camera.position.lerp(worldPos.clone().add(offset), 0.1);
camera.lookAt(worldPos);
```

### Billboard (always face camera)
```ts
const sprite = new THREE.Sprite(material);
// Or for meshes:
mesh.lookAt(camera.position);
```

### Fog
```ts
scene.fog = new THREE.Fog(0x000000, 10, 100);
// Or exponential:
scene.fog = new THREE.FogExp2(0x000000, 0.01);
```

### Skybox
```ts
scene.background = new THREE.CubeTextureLoader().setPath('/sky/')
  .load(['px.jpg','nx.jpg','py.jpg','ny.jpg','pz.jpg','nz.jpg']);
```

### Grid helper
```ts
const grid = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
scene.add(grid);
```

### Axes helper (debug)
```ts
scene.add(new THREE.AxesHelper(5));
```

### GUI / Debug Panel (lil-gui)
```ts
import GUI from 'lil-gui';
const gui = new GUI();
gui.add(light, 'intensity', 0, 10, 0.1);
gui.add(material, 'roughness', 0, 1, 0.01);
gui.addColor(material, 'color');
```

## React + Three.js

When using React with Three.js, prefer `@react-three/fiber` (R3F):

```bash
npm install @react-three/fiber @react-three/drei three
```

```tsx
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';

function App() {
  return (
    <Canvas shadows camera={{ position: [0, 5, 10], fov: 60 }}>
      <ambientLight intensity={0.3} />
      <directionalLight castShadow position={[10, 10, 5]} intensity={1} />
      <mesh castShadow position={[0, 0, 0]}>
        <boxGeometry />
        <meshStandardMaterial color="hotpink" />
      </mesh>
      <OrbitControls />
    </Canvas>
  );
}
```

## Color Space (important for r152+)

```ts
// Always set on renderer (r163+ default is SRGBColorSpace already)
renderer.outputColorSpace = THREE.SRGBColorSpace;

// Texture rules:
texture.colorSpace = THREE.SRGBColorSpace;        // color maps
texture.colorSpace = THREE.LinearSRGBColorSpace;  // normal, roughness, etc.
```

## Useful Addons

| Import path | Use |
|-------------|-----|
| `three/addons/controls/OrbitControls.js` | Mouse orbit camera |
| `three/addons/controls/PointerLockControls.js` | FPS controls |
| `three/addons/controls/FirstPersonControls.js` | WASD movement |
| `three/addons/loaders/GLTFLoader.js` | GLB/GLTF models |
| `three/addons/loaders/FBXLoader.js` | FBX models |
| `three/addons/loaders/RGBELoader.js` | HDR environment maps |
| `three/addons/loaders/DRACOLoader.js` | Draco mesh compression |
| `three/addons/postprocessing/EffectComposer.js` | Post-processing pipeline |
| `three/addons/utils/BufferGeometryUtils.js` | Merge geometries, compute tangents |
| `three/addons/libs/stats.module.js` | FPS/ms/mb monitor |
| `three/addons/libs/lil-gui.module.js` | Debug UI |

## Math / Vector Helpers

```ts
// Vectors
const v = new THREE.Vector3(1, 2, 3);
v.length();
v.normalize();
v.dot(otherVec);
v.cross(otherVec);
v.distanceTo(otherVec);
v.lerp(target, alpha);
v.clone();
v.set(x, y, z);

// Quaternions (rotation)
const q = new THREE.Quaternion();
q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI);
obj.quaternion.slerp(targetQuat, 0.1);

// Euler (easier rotation)
obj.rotation.set(0, Math.PI, 0);  // X, Y, Z
obj.rotation.x += 0.01;

// Colors
const color = new THREE.Color(0xff5500);
color.setHSL(0.6, 0.8, 0.5);
color.multiplyScalar(0.5);
```
