"""GLSL 330 shaders. Everything is drawn relative to the camera (camera at the origin)."""

LIGHTING = """
uniform vec3 u_sun_dir;
uniform vec3 u_sun_col;
uniform vec3 u_amb_top;
uniform vec3 u_amb_bot;
uniform vec3 u_fog_col;
uniform vec3 u_cloud_col;
uniform float u_fog_start;
uniform float u_fog_end;
uniform float u_cloud_y;
uniform float u_glow;
uniform float u_time;
uniform int u_nl;
uniform vec4 u_lp[32];
uniform vec3 u_lc[32];

vec3 shade(vec3 albedo, vec3 n, vec3 pos, float emit, float sky) {
    float diff = max(dot(n, u_sun_dir), 0.0);
    float wrap = max(dot(n, u_sun_dir) * 0.5 + 0.5, 0.0);
    float sun_k = smoothstep(0.5, 1.0, sky);
    vec3 light = mix(u_amb_bot, u_amb_top, n.y * 0.5 + 0.5) * 0.9 * (0.18 + 0.82 * sky)
               + u_sun_col * (diff * 0.55 * sun_k + wrap * 0.12 * sky);
    for (int i = 0; i < u_nl; i++) {
        vec3 L = u_lp[i].xyz - pos;
        float d = length(L);
        float att = clamp(1.0 - d / u_lp[i].w, 0.0, 1.0);
        att *= att;
        light += u_lc[i] * att * (0.35 + 0.65 * max(dot(n, L / max(d, 0.001)), 0.0));
    }
    float pulse = 0.85 + 0.15 * sin(u_time * 1.7 + pos.x * 0.3 + pos.z * 0.2);
    return albedo * light + albedo * emit * u_glow * pulse;
}

vec3 fogged(vec3 c, vec3 pos) {
    float d = length(pos);
    float f = smoothstep(u_fog_start, u_fog_end, d);
    float h = smoothstep(u_cloud_y + 9.0, u_cloud_y - 1.0, pos.y);
    c = mix(c, u_cloud_col, h * 0.85);
    return mix(c, u_fog_col, f);
}

vec3 tone(vec3 c) {
    return c / (1.0 + max(c - 0.8, 0.0) * 0.9);
}
"""

CHUNK_VS = """
#version 330
in vec3 in_pos;
in vec4 in_col;
in vec4 in_nrm;
in vec4 in_mat;
uniform mat4 u_vp;
uniform vec3 u_offset;
uniform float u_hand;
uniform float u_time;
uniform vec2 u_cam_mod;
uniform float u_cam_y;
out vec3 v_pos;
out vec3 v_wp;
flat out int v_mat;
flat out int v_front;
out float v_u;
out vec3 v_col;
out vec3 v_n;
out float v_emit;
out float v_rim;
out float v_sky;
void main() {
    v_pos = in_pos + u_offset;
    v_col = in_col.rgb;
    float a = floor(in_col.a * 255.0 + 0.5);
    v_emit = floor(a / 16.0) / 15.0;
    v_sky = mod(a, 16.0) / 15.0;
    v_n = in_nrm.xyz * 2.0 - 1.0;
    v_rim = in_nrm.w;
    v_mat = int(in_mat.x * 255.0 + 0.5);
    v_front = in_mat.z > 0.5 ? 1 : 0;
    v_u = in_mat.w;
    v_wp = v_pos + vec3(u_cam_mod.x, u_cam_y, u_cam_mod.y);
    float sway = in_mat.y;
    if (sway > 0.0 && u_hand < 0.5) {
        // plants and leaves move in a gentle breeze (anchored at their base)
        float h = (v_mat == 10) ? 1.0 : fract(v_wp.y / 0.7 + 0.01);
        float ph = u_time * 1.3 + v_wp.x * 0.35 + v_wp.z * 0.27;
        v_pos.xz += vec2(sin(ph), cos(ph * 0.8)) * sway * 0.08 * h;
    }
    gl_Position = u_vp * vec4(v_pos, 1.0);
    if (u_hand > 0.5) gl_Position.z = gl_Position.z * 0.02 - 0.97 * gl_Position.w;
}
"""

CHUNK_FS = """
#version 330
in vec3 v_pos;
in vec3 v_col;
in vec3 v_n;
in float v_emit;
in float v_rim;
in float v_sky;
in vec3 v_wp;
flat in int v_mat;
flat in int v_front;
in float v_u;
uniform float u_alpha;
uniform float u_nmat;
uniform int u_n_glass;
uniform int u_glasses[8];
uniform vec2 u_cam_mod;
uniform sampler2D u_atlas;
uniform sampler2D u_noise2;
uniform float u_atlas_rows;
uniform float u_detail;
out vec4 color;
""" + LIGHTING + """
void main() {
    vec3 n = normalize(v_n);
    vec3 albedo = v_col;
    float emit = v_emit;
    if (v_mat > 0 && u_detail > 0.0) {
        float dist = length(v_pos);
        float fade = 1.0 - smoothstep(40.0, 120.0, dist);
        // big soft colour drift across the land, so meadows and woods aren't one flat tone
        float drift = texture(u_noise2, v_wp.xz / 53.0).r;
        float big = (v_mat == 3 || v_mat == 10) ? 0.16 : 0.06;
        albedo *= 1.0 - big * 0.5 + big * drift;
        if (fade > 0.0) {
            float side = step(abs(n.y), 0.5);
            vec2 uv;
            if (side > 0.5) {
                uv = vec2(v_u, v_wp.y / 0.7 + 0.002);          // one tile per face, per layer
            } else {
                uv = v_wp.xz / 1.5;
            }
            if (v_mat == 11) uv += vec2(u_time * 0.05, u_time * 0.031);
            float k = (v_front == 1) ? (2.0 * u_nmat + float(v_mat)) : float(v_mat * 2) + side;
            vec2 tile = vec2(mod(k, 16.0), floor(k / 16.0));
            vec2 sz = vec2(16.0, u_atlas_rows);
            vec2 auv = (tile + (fract(uv) * 62.0 + 1.0) / 64.0) / sz;
            vec2 g = (62.0 / 64.0) / sz;
            vec2 tg = textureGrad(u_atlas, auv, dFdx(uv) * g, dFdy(uv) * g).rg;
            albedo *= mix(1.0, tg.r * 2.0, fade * u_detail);
            emit *= mix(1.0, tg.g * 2.0, fade * u_detail);
        }
    }
    vec3 c = shade(albedo, n, v_pos, emit, v_sky);
    bool is_glass = false;
    for (int i = 0; i < u_n_glass; i++) {
        if (v_mat == u_glasses[i]) is_glass = true;
    }
    float a = u_alpha;
    if (is_glass) {
        vec3 v = normalize(-v_pos);
        vec3 r = reflect(-v, n);
        float spec = pow(max(dot(r, u_sun_dir), 0.0), 60.0);
        c += u_sun_col * spec * 0.18;
        float fres = pow(1.0 - max(dot(v, n), 0.0), 4.0);
        // nearly fully transparent from every angle; only a faint rim
        a = mix(0.18, 0.40, fres);
        c = mix(c, u_fog_col, fres * 0.12);
    } else if (u_alpha < 0.99) {
        vec2 wp = v_pos.xz + u_cam_mod;
        float wave = sin(wp.x * 0.9 + u_time * 1.3) * sin(wp.y * 0.8 - u_time * 1.1);
        vec3 v = normalize(-v_pos);
        vec3 r = reflect(-v, n);
        float spec = pow(max(dot(r, u_sun_dir), 0.0), 40.0);
        c += u_sun_col * spec * 0.6 + vec3(0.04, 0.06, 0.08) * wave * n.y;
        float fres = pow(1.0 - max(dot(v, n), 0.0), 3.0);
        c = mix(c, u_fog_col, fres * 0.35);
        a = mix(u_alpha, 0.95, fres);
    }
    color = vec4(fogged(tone(c), v_pos), a);
}
"""

SKY_VS = """
#version 330
out vec2 v_ndc;
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2) * 2.0 - 1.0;
    v_ndc = p;
    gl_Position = vec4(p, 0.9999, 1.0);
}
"""

SKY_FS = """
#version 330
in vec2 v_ndc;
uniform mat4 u_inv;
uniform vec3 u_zenith;
uniform vec3 u_horizon;
uniform vec3 u_sun_dir;
uniform vec3 u_sun_col;
uniform vec3 u_moon_dir;
uniform float u_dusk;
uniform float u_time;
out vec4 color;
float hash(vec3 p) { return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
void main() {
    vec4 w = u_inv * vec4(v_ndc, 1.0, 1.0);
    vec3 d = normalize(w.xyz / w.w);
    float h = d.y;
    vec3 c = mix(u_horizon, u_zenith, pow(clamp(h, 0.0, 1.0), 0.55));
    c = mix(c, u_horizon * 0.92, clamp(-h * 3.0, 0.0, 1.0));
    // the sun: a soft lumen orb with a halo
    float s = max(dot(d, u_sun_dir), 0.0);
    c += u_sun_col * (pow(s, 900.0) * 3.0 + pow(s, 30.0) * 0.25 + pow(s, 4.0) * 0.08) * (1.0 - u_dusk * 0.6);
    // the hollow moon: a large pale ring with a faint disc, only in the dusk tide
    float m = dot(d, u_moon_dir);
    float ang = acos(clamp(m, -1.0, 1.0));
    float ringm = smoothstep(0.012, 0.0, abs(ang - 0.10)) + 0.35 * smoothstep(0.006, 0.0, abs(ang - 0.135));
    float disc = smoothstep(0.085, 0.075, ang) * 0.25;
    c += vec3(0.95, 0.90, 1.0) * (ringm * 0.9 + disc) * u_dusk;
    // stars
    vec3 g = floor(d * 220.0);
    float st = step(0.9965, hash(g)) * smoothstep(0.0, 0.25, h);
    float tw = 0.6 + 0.4 * sin(u_time * 2.0 + hash(g + 3.1) * 40.0);
    c += vec3(st * tw) * u_dusk * 0.9;
    // aurora ribbons in the dusk tide
    float band = sin(d.x * 4.0 + sin(d.z * 3.0 + u_time * 0.07) * 2.0 + u_time * 0.05);
    float au = smoothstep(0.6, 1.0, band) * smoothstep(0.15, 0.45, h) * smoothstep(0.95, 0.5, h);
    c += mix(vec3(0.2, 0.9, 0.7), vec3(0.7, 0.4, 1.0), d.z * 0.5 + 0.5) * au * 0.35 * u_dusk;
    color = vec4(c, 1.0);
}
"""

CLOUD_VS = """
#version 330
in vec2 in_pos;
uniform mat4 u_vp;
uniform vec2 u_snap;
uniform vec2 u_cam_mod;
uniform float u_cloud_y;
uniform float u_time;
uniform sampler2D u_noise;
out vec3 v_pos;
out float v_h;
const float PERIOD = 1024.0;
float sample_h(vec2 wp) {
    float a = texture(u_noise, (wp + vec2(u_time * 1.1, u_time * 0.4)) / PERIOD).r;
    float b = texture(u_noise, (wp * 4.0 - vec2(u_time * 2.3, -u_time * 1.7)) / PERIOD).g;
    return a * 0.75 + b * 0.25;
}
void main() {
    vec2 rel = in_pos - u_snap;
    vec2 wp = rel + u_cam_mod;
    float h = sample_h(wp);
    v_h = h;
    float y = u_cloud_y + (h - 0.5) * 9.0;
    v_pos = vec3(rel.x, y, rel.y);
    gl_Position = u_vp * vec4(v_pos, 1.0);
}
"""

CLOUD_FS = """
#version 330
in vec3 v_pos;
in float v_h;
uniform vec3 u_sun_col;
uniform vec3 u_amb_top;
uniform vec3 u_cloud_col;
uniform vec3 u_fog_col;
uniform vec3 u_deep_col;
uniform float u_fog_end;
uniform float u_dusk;
out vec4 color;
void main() {
    vec3 dx = dFdx(v_pos), dy = dFdy(v_pos);
    vec3 n = normalize(cross(dx, dy));
    if (n.y < 0.0) n = -n;
    float t = smoothstep(0.25, 0.85, v_h);
    vec3 c = mix(u_deep_col, u_cloud_col, t);
    c *= 0.75 + 0.25 * n.y;
    c += u_sun_col * pow(t, 3.0) * 0.12;
    float d = length(v_pos.xz);
    float f = smoothstep(u_fog_end * 0.35, u_fog_end * 1.4, d);
    color = vec4(mix(c, u_fog_col, f), 1.0);
}
"""

LINE_VS = """
#version 330
in vec3 in_pos;
uniform mat4 u_vp;
uniform vec3 u_offset;
void main() { gl_Position = u_vp * vec4(in_pos + u_offset, 1.0); }
"""

LINE_FS = """
#version 330
uniform vec4 u_color;
out vec4 color;
void main() { color = u_color; }
"""

POINT_VS = """
#version 330
in vec3 in_pos;
in vec4 in_col;
in float in_size;
uniform mat4 u_vp;
uniform float u_scale;
out vec4 v_col;
void main() {
    gl_Position = u_vp * vec4(in_pos, 1.0);
    gl_PointSize = clamp(in_size * u_scale / max(gl_Position.w, 0.1), 1.0, 64.0);
    v_col = in_col;
}
"""

POINT_FS = """
#version 330
in vec4 v_col;
out vec4 color;
void main() {
    vec2 p = gl_PointCoord * 2.0 - 1.0;
    float r = dot(p, p);
    if (r > 1.0) discard;
    float a = exp(-r * 3.0);
    color = vec4(v_col.rgb, v_col.a * a);
}
"""

UI_VS = """
#version 330
in vec2 in_pos;
in vec2 in_local;
in vec4 in_shape;     // half width, half height, corner radius, kind
in vec4 in_col;
in vec4 in_col2;      // border colour (a = border width in px)
uniform vec2 u_screen;
out vec2 v_local;
flat out vec4 v_shape;
out vec4 v_col;
flat out vec4 v_col2;
void main() {
    gl_Position = vec4(in_pos / u_screen * 2.0 - 1.0, 0.0, 1.0);
    v_local = in_local;
    v_shape = in_shape;
    v_col = in_col;
    v_col2 = in_col2;
}
"""

UI_FS = """
#version 330
in vec2 v_local;
flat in vec4 v_shape;
in vec4 v_col;
flat in vec4 v_col2;
uniform sampler2D u_tex;
out vec4 color;
float sd_round(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}
float sd_hex(vec2 p, float r) {      // pointy-top hexagon, circumradius r
    const vec3 k = vec3(-0.866025404, 0.5, 0.577350269);
    p = abs(p.yx);
    p -= 2.0 * min(dot(k.xy, p), 0.0) * k.xy;
    float ri = r * 0.866025404;
    p -= vec2(clamp(p.x, -k.z * ri, k.z * ri), ri);
    return length(p) * sign(p.y);
}
void main() {
    float kind = v_shape.w;
    if (kind > 4.5) {                       // textured quad (thumbnails); local = uv
        color = texture(u_tex, v_local) * v_col;
        return;
    }
    float d;
    if (kind < 0.5) d = sd_round(v_local, v_shape.xy, v_shape.z);
    else if (kind < 1.5) d = sd_hex(v_local, v_shape.x);
    else if (kind < 2.5) d = length(v_local) - v_shape.x;
    else {                                  // soft shadow
        d = sd_round(v_local, v_shape.xy, v_shape.z);
        float a = 1.0 - smoothstep(-v_shape.z * 0.2, v_shape.z, d);
        color = vec4(v_col.rgb, v_col.a * a * a);
        return;
    }
    float aa = 1.0;
    float fill = 1.0 - smoothstep(-aa * 0.5, aa * 0.5, d);
    vec4 c = v_col;
    float bw = v_col2.a;
    if (bw > 0.0) {
        float inner = smoothstep(-bw - 0.5, -bw + 0.5, d);
        c = mix(c, vec4(v_col2.rgb, max(c.a, 0.9)), inner);
    }
    color = vec4(c.rgb, c.a * fill);
}
"""
