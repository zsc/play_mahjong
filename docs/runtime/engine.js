(function(Object){
   typeof globalThis !== "object"
   &&
    (this
      ? get()
      : (Object.defineProperty
         (Object.prototype, "_T_", {configurable: true, get: get}),
        _T_));
   function get(){
    var global = this || self;
    global.globalThis = global;
    delete Object.prototype._T_;
   }
  }
  (Object));
export const ready = (js=>
      async args=>{
       "use strict";
       const
        {link, src, generated, enable_jspi, native_effects} = args,
        isNode = globalThis.process?.versions?.node,
        math =
          {cos: Math.cos,
           sin: Math.sin,
           tan: Math.tan,
           acos: Math.acos,
           asin: Math.asin,
           atan: Math.atan,
           cosh: Math.cosh,
           sinh: Math.sinh,
           tanh: Math.tanh,
           acosh: Math.acosh,
           asinh: Math.asinh,
           atanh: Math.atanh,
           cbrt: Math.cbrt,
           exp: Math.exp,
           expm1: Math.expm1,
           log: Math.log,
           log1p: Math.log1p,
           log2: Math.log2,
           log10: Math.log10,
           atan2: Math.atan2,
           hypot: Math.hypot,
           pow: Math.pow,
           fmod: (x, y)=>x % y},
        typed_arrays =
          [Float32Array,
           Float64Array,
           Int8Array,
           Uint8Array,
           Int16Array,
           Uint16Array,
           Int32Array,
           Int32Array,
           Int32Array,
           Int32Array,
           Float32Array,
           Float64Array,
           Uint8Array,
           Uint16Array,
           Uint8ClampedArray],
        fs = isNode && require("node:fs"),
        on_windows = isNode && globalThis.process.platform === "win32",
        virtual_files = new Map(),
        virtual_dirs = new Set(),
        virtual_fds = new Map();
       let next_virtual_fd = 1000000;
       const
        virtual_path = on_windows ? p=>p.replaceAll("\\", "/") : p=>p,
        console_name =
          on_windows
           ? p=>{
             const
              m = /^(?:[\\/]{2}[.?][\\/])?(CON|CONIN\$|CONOUT\$)$/i.exec(p);
             return m ? `\\\\.\\${m[1].toUpperCase()}` : p;}
           : p=>p;
       function register_virtual_file(name, content){
        name = virtual_path(name);
        virtual_files.set(name, content);
        let dir = name;
        while(true){
         const i = dir.lastIndexOf("/");
         if(i <= 0) break;
         dir = dir.slice(0, i);
         virtual_dirs.add(dir);
        }
       }
       if(args.files)
        for(const [name, data] of Object.entries(args.files))
         register_virtual_file
          (name, Uint8Array.from(atob(data), c=>c.charCodeAt(0)));
       const
        fs_cst = fs?.constants,
        access_flags =
          fs ? [fs_cst.R_OK, fs_cst.W_OK, fs_cst.X_OK, fs_cst.F_OK] : [],
        open_flags =
          fs
           ? [fs_cst.O_RDONLY,
             fs_cst.O_WRONLY,
             fs_cst.O_RDWR,
             fs_cst.O_APPEND,
             fs_cst.O_CREAT,
             fs_cst.O_TRUNC,
             fs_cst.O_EXCL,
             fs_cst.O_NONBLOCK,
             fs_cst.O_NOCTTY,
             fs_cst.O_DSYNC,
             fs_cst.O_SYNC]
           : [];
       var
        out_channels =
          {map: new WeakMap(),
           set: new Set(),
           finalization:
           new FinalizationRegistry(ref=>out_channels.set.delete(ref))};
       function register_channel(ch){
        const ref = new WeakRef(ch);
        out_channels.map.set(ch, ref);
        out_channels.set.add(ref);
        out_channels.finalization.register(ch, ref, ch);
       }
       function unregister_channel(ch){
        const ref = out_channels.map.get(ch);
        if(ref){
         out_channels.map.delete(ch);
         out_channels.set.delete(ref);
         out_channels.finalization.unregister(ch);
        }
       }
       function channel_list(){
        return [...out_channels.set].map(ref=>ref.deref()).filter(ch=>ch);
       }
       var start_fiber;
       function make_suspending(f){
        return enable_jspi && WebAssembly?.Suspending
                ? new WebAssembly.Suspending(f)
                : f;
       }
       function make_promising(f){
        return enable_jspi && WebAssembly?.promising && f
                ? WebAssembly.promising(f)
                : f;
       }
       const
        decoder = new TextDecoder("utf-8", {ignoreBOM: 1}),
        encoder = new TextEncoder();
       var scratch = new Uint8Array(0);
       function scratch_buffer(){
        if(scratch.byteLength === 0)
         scratch =
          new Uint8Array(caml_buffer.buffer, 0, caml_buffer_size.value);
        return scratch;
       }
       function hash_int(h, d){
        d = Math.imul(d, 0xcc9e2d51 | 0);
        d = d << 15 | d >>> 17;
        d = Math.imul(d, 0x1b873593);
        h ^= d;
        h = h << 13 | h >>> 19;
        return (h + (h << 2) | 0) + (0xe6546b64 | 0) | 0;
       }
       function jsstring_is_bytes(s){
        for(var i = 0; i < s.length; i++)
         if(s.charCodeAt(i) > 0xff) return false;
        return true;
       }
       function caml_hash_mix_jsbytes(h, s){
        var len = s.length, i, w;
        for(i = 0; i + 4 <= len; i += 4){
         w =
          s.charCodeAt(i) | s.charCodeAt(i + 1) << 8
          | s.charCodeAt(i + 2) << 16
          | s.charCodeAt(i + 3) << 24;
         h = hash_int(h, w);
        }
        w = 0;
        switch(len & 3){
          case 3:
           w = s.charCodeAt(i + 2) << 16;
          case 2:
           w |= s.charCodeAt(i + 1) << 8;
          case 1:
           w |= s.charCodeAt(i); h = hash_int(h, w);
        }
        return h ^ len;
       }
       function hash_string(h, s){
        if(jsstring_is_bytes(s)) return caml_hash_mix_jsbytes(h, s);
        var len = s.length, i, w;
        for(i = 0; i + 2 <= len; i += 2){
         w = s.charCodeAt(i) | s.charCodeAt(i + 1) << 16;
         h = hash_int(h, w);
        }
        if(len & 1) h = hash_int(h, s.charCodeAt(i));
        return h ^ len;
       }
       function getenv(n){
        return isNode && globalThis.process.env[n] !== undefined
                ? globalThis.process.env[n]
                : globalThis.jsoo_env?.[n];
       }
       let record_backtrace_flag = 0;
       for(const l of getenv("OCAMLRUNPARAM")?.split(",") || []){
        if(l === "b") record_backtrace_flag = 1;
        if(l.startsWith("b=")) record_backtrace_flag = + l.slice(2) ? 1 : 0;
       }
       function alloc_stat(s, large){
        var kind;
        if(s.isFile())
         kind = 0;
        else if(s.isDirectory())
         kind = 1;
        else if(s.isCharacterDevice())
         kind = 2;
        else if(s.isBlockDevice())
         kind = 3;
        else if(s.isSymbolicLink())
         kind = 4;
        else if(s.isFIFO()) kind = 5; else if(s.isSocket()) kind = 6;
        return caml_alloc_stat
                (large,
                 s.dev,
                 s.ino | 0,
                 kind,
                 s.mode & 0o7777,
                 s.nlink,
                 s.uid,
                 s.gid,
                 s.rdev,
                 BigInt(s.size),
                 s.atimeMs / 1000,
                 s.mtimeMs / 1000,
                 s.ctimeMs / 1000);
       }
       const
        on_arm64 = globalThis.process?.arch === "arm64",
        isV8 = new Error().stack?.includes("\n    at ") ?? false,
        call = Function.prototype.call,
        DV = DataView.prototype;
       function callback(f, count, args, kind){
        if(! native_effects) return caml_callback(f, count, args, kind);
        const saved = effect_allowed.value;
        effect_allowed.value = 0;
        try{return caml_callback(f, count, args, kind);}
        finally{effect_allowed.value = saved;}
       }
       const
        bindings =
          {jstag:
           WebAssembly.JSTag
           || new WebAssembly.Tag({parameters: ["externref"], results: []}),
           identity: x=>x,
           from_bool: x=>! ! x,
           get: (x, y)=>x[y],
           set: (x, y, z)=>x[y] = z,
           delete: (x, y)=>delete x[y],
           instanceof: (x, y)=>x instanceof y,
           is_js_error: x=>x instanceof Error,
           to_js_string: x=>String(x),
           typeof: x=>typeof x,
           equals: (x, y)=>x == y,
           strict_equals: (x, y)=>x === y,
           fun_call: (f, o, args)=>f.apply(o, args),
           meth_call: (o, f, args)=>o[f].apply(o, args),
           new_array: n=>new Array(n),
           new_obj: ()=>({}),
           new: (c, args)=>new c(...args),
           global_this: globalThis,
           iter_props:
           (o, f)=>{for(var nm in o) if(Object.hasOwn(o, nm)) f(nm);},
           array_length: a=>a.length,
           array_get: (a, i)=>a[i],
           array_set: (a, i, v)=>a[i] = v,
           read_string: l=>decoder.decode(scratch_buffer().subarray(0, l)),
           read_string_stream:
           (l, stream)=>
              decoder.decode
               (scratch_buffer().subarray(0, l), {stream: stream}),
           append_string: (s1, s2)=>s1 + s2,
           write_string:
           s=>{
            var start = 0, len = s.length;
            for(;;){
             const
              {read, written} =
                encoder.encodeInto(s.slice(start), scratch_buffer());
             len -= read;
             if(! len) return written;
             caml_extract_bytes(written);
             start += read;
            }},
           ta_create: (k, sz)=>new typed_arrays[k](sz),
           ta_normalize:
           a=>
              a instanceof Uint32Array
               ? new Int32Array(a.buffer, a.byteOffset, a.length)
               : a,
           ta_kind: a=>typed_arrays.findIndex(c=>a instanceof c),
           ta_length: a=>a.length,
           ta_get_i32: (a, i)=>a[i],
           ta_fill: (a, v)=>a.fill(v),
           ta_blit: (s, d)=>d.set(s),
           ta_subarray: (a, i, j)=>a.subarray(i, j),
           ta_set: (a, b, i)=>a.set(b, i),
           ta_new: len=>new Uint8Array(len),
           ta_copy: (ta, t, s, e)=>ta.copyWithin(t, s, e),
           ta_bytes:
           a=>
              new
               Uint8Array
               (a.buffer, a.byteOffset, a.length * a.BYTES_PER_ELEMENT),
           dv_make: a=>new DataView(a.buffer, a.byteOffset, a.byteLength),
           dv_get_f64: call.bind(DV.getFloat64),
           dv_get_f32: call.bind(DV.getFloat32),
           dv_get_i64: call.bind(DV.getBigInt64),
           dv_get_i32:
           isV8 ? call.bind(DV.getInt32) : (x, y, z)=>x.getInt32(y, z),
           dv_get_i16: call.bind(DV.getInt16),
           dv_get_ui16: call.bind(DV.getUint16),
           dv_get_i8: call.bind(DV.getInt8),
           dv_get_ui8: call.bind(DV.getUint8),
           dv_set_f64: call.bind(DV.setFloat64),
           dv_set_f32: call.bind(DV.setFloat32),
           dv_set_i64: call.bind(DV.setBigInt64),
           dv_set_i32: call.bind(DV.setInt32),
           dv_set_i16: call.bind(DV.setInt16),
           dv_set_i8: call.bind(DV.setInt8),
           littleEndian: new Uint8Array(new Uint32Array([1]).buffer)[0],
           wrap_callback:
           f=>
              function(...args){
               if(args.length === 0) args = [undefined];
               return callback(f, args.length, args, 1);
              },
           wrap_callback_args:
           f=>function(...args){return callback(f, 1, [args], 0);},
           wrap_callback_strict:
           (arity, f)=>
              function(...args){
               args.length = arity;
               return callback(f, arity, args, 0);
              },
           wrap_callback_unsafe:
           f=>function(...args){return callback(f, args.length, args, 2);},
           wrap_meth_callback:
           f=>
              function(...args){
               args.unshift(this);
               return callback(f, args.length, args, 1);
              },
           wrap_meth_callback_args:
           f=>function(...args){return callback(f, 2, [this, args], 0);},
           wrap_meth_callback_strict:
           (arity, f)=>
              function(...args){
               args.length = arity;
               args.unshift(this);
               return callback(f, args.length, args, 0);
              },
           wrap_meth_callback_unsafe:
           f=>
              function(...args){
               args.unshift(this);
               return callback(f, args.length, args, 2);
              },
           wrap_fun_arguments: f=>function(...args){return f(args);},
           format_float:
           (prec, conversion, pad, x)=>{
            function decompose(x){
             var dv = new DataView(new ArrayBuffer(8));
             dv.setFloat64(0, x);
             var
              hi = dv.getUint32(0),
              lo = dv.getUint32(4),
              eb = hi >>> 20 & 0x7ff,
              m = BigInt(hi & 0xfffff) << 32n | BigInt(lo);
             return eb === 0 ? [m, - 1074] : [m | 1n << 52n, eb - 1075];
            }
            function exact_scaled(x, k){
             var d = decompose(x), num = d[0], den = 1n;
             if(k >= 0)
              num *= 10n ** BigInt(k);
             else
              den = 10n ** BigInt(- k);
             if(d[1] >= 0) num <<= BigInt(d[1]); else den <<= BigInt(- d[1]);
             var q = num / den, r2 = num % den * 2n;
             if(r2 > den || r2 === den && q & 1n) q += 1n;
             return q;
            }
            function exact_fixed(x, prec){
             var q = exact_scaled(x, prec).toString();
             if(prec === 0) return q;
             if(q.length <= prec) q = "0".repeat(prec + 1 - q.length) + q;
             return q.slice(0, q.length - prec) + "."
                    + q.slice(q.length - prec);
            }
            function exact_exponential(x, prec){
             if(x === 0)
              return (prec > 0 ? "0." + "0".repeat(prec) : "0") + "e+0";
             var e10 = Math.floor(Math.log10(x));
             for(;;){
              var s = exact_scaled(x, prec - e10).toString();
              if(s.length === prec + 1){
               var m = prec > 0 ? s.charAt(0) + "." + s.slice(1) : s;
               return m + "e" + (e10 < 0 ? "-" : "+") + Math.abs(e10);
              }
              e10 += s.length - (prec + 1);
             }
            }
            function toExponential(x, prec){
             return prec > 100
                     ? exact_exponential(x, prec)
                     : x.toExponential(prec);
            }
            function toFixed(x, dp){
             return dp > 100 || x >= 1e21 ? exact_fixed(x, dp) : x.toFixed(dp);
            }
            switch(conversion){
              case 0:
               var s = toExponential(x, prec), i = s.length;
               if(s.charAt(i - 3) === "e")
                s = s.slice(0, i - 1) + "0" + s.slice(i - 1);
               break;
              case 1:
               s = toFixed(x, prec); break;
              case 2:
               prec = prec ? prec : 1;
               s = toExponential(x, prec - 1);
               var j = s.indexOf("e"), exp = + s.slice(j + 1);
               if(exp < - 4 || x >= 1e21 || x.toFixed(0).length > prec){
                var i = j - 1;
                while(s.charAt(i) === "0") i--;
                if(s.charAt(i) === ".") i--;
                s = s.slice(0, i + 1) + s.slice(j);
                i = s.length;
                if(s.charAt(i - 3) === "e")
                 s = s.slice(0, i - 1) + "0" + s.slice(i - 1);
                break;
               }
               else{
                var p = prec;
                if(exp < 0){
                 p -= exp + 1;
                 s = toFixed(x, p);
                }
                else
                 while(s = toFixed(x, p), s.length > prec + 1) p--;
                if(p){
                 var i = s.length - 1;
                 while(s.charAt(i) === "0") i--;
                 if(s.charAt(i) === ".") i--;
                 s = s.slice(0, i + 1);
                }
               }
               break;
            }
            return pad ? " " + s : s;},
           gettimeofday: ()=>Date.now() / 1000,
           times:
           ()=>{
            if(globalThis.process?.cpuUsage){
             var t = globalThis.process.cpuUsage();
             return caml_alloc_times(t.user / 1e6, t.system / 1e6);
            }
            else{
             var t = performance.now() / 1000;
             return caml_alloc_times(t, 0);
            }},
           gmtime:
           t=>{
            var
             d = new Date(t * 1000),
             d_num = d.getTime(),
             januaryfirst =
               new Date(Date.UTC(d.getUTCFullYear(), 0, 1)).getTime(),
             doy = Math.floor((d_num - januaryfirst) / 86400000);
            return caml_alloc_tm
                    (d.getUTCSeconds(),
                     d.getUTCMinutes(),
                     d.getUTCHours(),
                     d.getUTCDate(),
                     d.getUTCMonth(),
                     d.getUTCFullYear() - 1900,
                     d.getUTCDay(),
                     doy,
                     false);},
           localtime:
           t=>{
            var
             d = new Date(t * 1000),
             doy =
               Math.floor
                ((Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())
                 - Date.UTC(d.getFullYear(), 0, 1))
                 / 86400000),
             jan = new Date(d.getFullYear(), 0, 1),
             jul = new Date(d.getFullYear(), 6, 1),
             stdTimezoneOffset =
               Math.max(jan.getTimezoneOffset(), jul.getTimezoneOffset()),
             isdst = d.getTimezoneOffset() < stdTimezoneOffset;
            if
             (stdTimezoneOffset === 0
              && jan.getTimezoneOffset() !== jul.getTimezoneOffset()
              &&
               globalThis.Intl?.DateTimeFormat?.().resolvedOptions().timeZone
               === "Europe/Dublin")
             isdst = ! isdst;
            return caml_alloc_tm
                    (d.getSeconds(),
                     d.getMinutes(),
                     d.getHours(),
                     d.getDate(),
                     d.getMonth(),
                     d.getFullYear() - 1900,
                     d.getDay(),
                     doy,
                     isdst);},
           mktime:
           (year, month, day, h, m, s)=>
              new Date(year, month, day, h, m, s).getTime(),
           random_seed: ()=>crypto.getRandomValues(new Int32Array(12)),
           access:
           (p, flags)=>
              fs.accessSync
               (p,
                access_flags.reduce((f, v, i)=>flags & 1 << i ? f | v : f, 0)),
           open:
           (p, flags, perm)=>{
            const vp = virtual_path(p);
            if(virtual_files.has(vp) && ! (flags & 2)){
             const fd = next_virtual_fd++;
             virtual_fds.set(fd, {data: virtual_files.get(vp), offset: 0});
             return fd;
            }
            return fs.openSync
                    (console_name(p),
                     open_flags.reduce((f, v, i)=>flags & 1 << i ? f | v : f, 0),
                     perm);},
           close:
           fd=>{
            if(virtual_fds.has(fd)){virtual_fds.delete(fd); return;}
            fs.closeSync(fd);},
           write:
           (fd, b, o, l, p)=>
              fs
               ? fs.writeSync(fd, b, o, l, p === null ? p : Number(p))
               : (console
                   [fd === 2 ? "error" : "log"]
                  (typeof b === "string"
                    ? b
                    : decoder.decode(b.slice(o, o + l))),
                 l),
           read:
           (fd, b, o, l, p)=>{
            const vf = virtual_fds.get(fd);
            if(vf){
             const
              pos = p === null ? vf.offset : Number(p),
              n = Math.min(l, vf.data.length - pos);
             if(n <= 0) return 0;
             b.set(vf.data.subarray(pos, pos + n), o);
             vf.offset = pos + n;
             return n;
            }
            return fs.readSync(fd, b, o, l, p);},
           fsync: fd=>fs.fsyncSync(fd),
           file_size:
           fd=>{
            const vf = virtual_fds.get(fd);
            return vf
                    ? BigInt(vf.data.length)
                    : fs.fstatSync(fd, {bigint: true}).size;},
           register_channel: register_channel,
           unregister_channel: unregister_channel,
           channel_list: channel_list,
           exit: n=>isNode && globalThis.process.exit(n),
           argv: ()=>isNode ? globalThis.process.argv.slice(1) : ["a.out"],
           on_windows: + on_windows,
           on_arm64: + on_arm64,
           getenv: getenv,
           backtrace_status: ()=>record_backtrace_flag,
           record_backtrace: b=>record_backtrace_flag = b,
           system:
           c=>{
            var
             res =
               require("node:child_process").spawnSync
                (c, {shell: true, stdio: "inherit"});
            if(res.error) throw res.error;
            return res.signal ? 255 : res.status;},
           isatty: fd=>isNode ? + require("node:tty").isatty(fd) : 0,
           getuid:
           ()=>globalThis.process?.getuid ? globalThis.process.getuid() : 1,
           geteuid:
           ()=>globalThis.process?.geteuid ? globalThis.process.geteuid() : 1,
           getgid:
           ()=>globalThis.process?.getgid ? globalThis.process.getgid() : 1,
           getegid:
           ()=>globalThis.process?.getegid ? globalThis.process.getegid() : 1,
           time: ()=>performance.now(),
           getcwd: ()=>isNode ? globalThis.process.cwd() : "/static",
           chdir: x=>globalThis.process.chdir(x),
           mkdir: (p, m)=>fs.mkdirSync(p, m),
           rmdir: p=>fs.rmdirSync(p),
           link: (d, s)=>fs.linkSync(d, s),
           symlink:
           (t, p, kind)=>fs.symlinkSync(t, p, [null, "file", "dir"][kind]),
           readlink: p=>fs.readlinkSync(p),
           unlink: p=>fs.unlinkSync(p),
           read_dir:
           p=>{
            const
             vp = virtual_path(p),
             prefix = vp.endsWith("/") ? vp : vp + "/",
             entries = new Set();
            for(const name of virtual_files.keys())
             if(name.startsWith(prefix)){
              const
               rest = name.slice(prefix.length),
               slash = rest.indexOf("/");
              entries.add(slash < 0 ? rest : rest.slice(0, slash));
             }
            if(fs)
             try{for(const e of fs.readdirSync(p)) entries.add(e);}
             catch(e){if(entries.size === 0) throw e;}
            return [...entries];},
           opendir: p=>({dir: fs.opendirSync(p), dots: [".", ".."]}),
           readdir:
           d=>{
            if(d.dots.length > 0) return d.dots.shift();
            var n = d.dir.readSync()?.name;
            return n === undefined ? null : n;},
           closedir: d=>{d.dots = []; d.dir.closeSync();},
           stat: (p, l)=>alloc_stat(fs.statSync(p), l),
           lstat: (p, l)=>alloc_stat(fs.lstatSync(p), l),
           fstat: (fd, l)=>alloc_stat(fs.fstatSync(fd), l),
           chmod: (p, perms)=>fs.chmodSync(p, perms),
           fchmod: (p, perms)=>fs.fchmodSync(p, perms),
           file_exists:
           p=>{
            const vp = virtual_path(p);
            return virtual_files.has(vp) || virtual_dirs.has(vp)
                    ? 1
                    : fs ? + fs.existsSync(p) : 0;},
           filepath_exists:
           p=>{
            const vp = virtual_path(p);
            if(virtual_files.has(vp) || virtual_dirs.has(vp)) return 1;
            if(! fs) return 0;
            try{fs.statSync(p); return 1;}
            catch(e){
             if(e.code === "ENOENT" || e.code === "ENOTDIR") return 0;
             throw e;
            }},
           is_directory:
           p=>{
            const vp = virtual_path(p);
            return virtual_dirs.has(vp)
                    ? 1
                    : virtual_files.has(vp) ? 0 : + fs.statSync(p).isDirectory();},
           is_file:
           p=>{
            const vp = virtual_path(p);
            return virtual_files.has(vp)
                    ? 1
                    : virtual_dirs.has(vp) ? 0 : + fs.statSync(p).isFile();},
           utimes: (p, a, m)=>fs.utimesSync(p, a, m),
           truncate: (p, l)=>fs.truncateSync(p, l),
           ftruncate: (fd, l)=>fs.ftruncateSync(fd, l),
           rename:
           (o, n)=>{
            var n_stat;
            if
             (on_windows && (n_stat = fs.statSync(n, {throwIfNoEntry: false}))
              && fs.statSync(o, {throwIfNoEntry: false})?.isDirectory())
             if(n_stat.isDirectory()){
              if(! n.startsWith(o)) try{fs.rmdirSync(n);}catch{}
             }
             else{
              var
               e =
                 new
                  Error
                  (`ENOTDIR: not a directory, rename '${o}' -> '${n}'`);
              throw Object.assign
                     (e,
                      {errno: - 20, code: "ENOTDIR", syscall: "rename", path: n});
             }
            fs.renameSync(o, n);},
           tmpdir: ()=>require("node:os").tmpdir(),
           start_fiber: x=>start_fiber(x),
           suspend_fiber: make_suspending((f, env)=>new Promise(k=>f(k, env))),
           resume_fiber: (k, v)=>k(v),
           weak_new: v=>new WeakRef(v),
           weak_deref:
           w=>{var v = w.deref(); return v === undefined ? null : v;},
           weak_map_new: ()=>new WeakMap(),
           map_new: ()=>new Map(),
           map_get:
           (m, x)=>{var v = m.get(x); return v === undefined ? null : v;},
           map_set: (m, x, v)=>m.set(x, v),
           map_get_or_set:
           (m, x, v)=>{
            var r = m.get(x);
            if(r === undefined){m.set(x, v); return null;}
            return r;},
           map_delete: (m, x)=>m.delete(x),
           hash_string: hash_string,
           log: x=>console.log(x),
           register_fragments:
           (unitName, fragmentsSource)=>{
            const frags = eval?.(fragmentsSource);
            imports[unitName + ".fragments"] = frags;},
           load_module:
           wasmBytes=>{
            const
             module = new WebAssembly.Module(wasmBytes, options),
             inst = new WebAssembly.Instance(module, imports);
            Object.assign(imports.OCaml, inst.exports);
            return inst.exports["_dynlink.init"]();},
           load_wasmo:
           zipBytes=>{
            const
             dv =
               new
                DataView
                (zipBytes.buffer, zipBytes.byteOffset, zipBytes.byteLength),
             len = zipBytes.byteLength;
            let eocdOff = len - 22;
            while(eocdOff >= 0 && dv.getUint32(eocdOff, true) !== 0x06054b50)
             eocdOff--;
            if(eocdOff < 0) throw new Error("Invalid ZIP: EOCD not found");
            const
             cdOff = dv.getUint32(eocdOff + 16, true),
             cdEntries = dv.getUint16(eocdOff + 10, true),
             entries = {};
            let off = cdOff;
            for(let i = 0; i < cdEntries; i++){
             if(dv.getUint32(off, true) !== 0x02014b50)
              throw new Error("Invalid ZIP: bad CD entry");
             const
              nameLen = dv.getUint16(off + 28, true),
              extraLen = dv.getUint16(off + 30, true),
              commentLen = dv.getUint16(off + 32, true),
              localOff = dv.getUint32(off + 42, true),
              name =
                decoder.decode
                 (zipBytes.subarray(off + 46, off + 46 + nameLen)),
              size = dv.getUint32(off + 24, true),
              localNameLen = dv.getUint16(localOff + 26, true),
              localExtraLen = dv.getUint16(localOff + 28, true),
              dataOff = localOff + 30 + localNameLen + localExtraLen;
             entries[name] = zipBytes.subarray(dataOff, dataOff + size);
             off += 46 + nameLen + extraLen + commentLen;
            }
            if(! entries["code.wasm"])
             throw new Error("code.wasm not found in .wasmo");
            const
             module = new WebAssembly.Module(entries["code.wasm"], options),
             inst = new WebAssembly.Instance(module, imports);
            Object.assign(imports.OCaml, inst.exports);
            const names = decoder.decode(entries.link_order).split("\x00");
            for(const name of names) inst.exports[name + ".init"]();},
           register_file: (name, data)=>register_virtual_file(name, data),
           read_file: name=>virtual_files.get(virtual_path(name)) ?? null},
        string_ops =
          {test: v=>+ (typeof v === "string"),
           compare: (s1, s2)=>s1 < s2 ? - 1 : + (s1 > s2),
           decodeStringFromUTF8Array: ()=>"",
           encodeStringToUTF8Array: ()=>0,
           fromCharCodeArray: ()=>"",
           length: s=>s.length,
           intoCharCodeArray: ()=>0},
        imports =
          Object.assign
           ({Math: math,
             bindings: bindings,
             js: js,
             "wasm:js-string": string_ops,
             "wasm:text-decoder": string_ops,
             "wasm:text-encoder": string_ops,
             str: new globalThis.Proxy({}, {get(_, prop){return prop;}}),
             env: {}},
            generated),
        options =
          {builtins: ["js-string", "text-decoder", "text-encoder"],
           importedStringConstants: "str"};
       function loadRelative(src){
        const
         path = require("node:path"),
         f = path.join(path.dirname(module.filename), src);
        return require("node:fs/promises").readFile(f);
       }
       const fetchBase = globalThis?.document?.currentScript?.src;
       function fetchRelative(src){
        const url = fetchBase ? new URL(src, fetchBase) : src;
        return fetch(url);
       }
       const loadCode = isNode ? loadRelative : fetchRelative;
       async function instantiateModule(code){
        return isNode
                ? WebAssembly.instantiate(await code, imports, options)
                : WebAssembly.instantiateStreaming(code, imports, options);
       }
       async function instantiateFromDir(){
        imports.OCaml = {};
        const deps = [];
        async function loadModule(module, isRuntime){
         const sync = module[1].constructor !== Array;
         async function instantiate(){
          const code = loadCode(src + "/" + module[0] + ".wasm");
          await Promise.all(sync ? deps : module[1].map(i=>deps[i]));
          const wasmModule = await instantiateModule(code);
          Object.assign
           (isRuntime ? imports.env : imports.OCaml,
            wasmModule.instance.exports);
         }
         const promise = instantiate();
         deps.push(promise);
         return promise;
        }
        async function loadModules(lst){
         for(const module of lst) await loadModule(module);
        }
        await loadModule(link[0], 1);
        if(link.length > 1){
         await loadModule(link[1]);
         const
          workers =
            new Array(20).fill(link.slice(2).values()).map(loadModules);
         await Promise.all(workers);
        }
        return {instance: {exports: Object.assign(imports.env, imports.OCaml)}};
       }
       const wasmModule = await instantiateFromDir();
       var
        {caml_callback,
          effect_allowed,
          caml_alloc_times,
          caml_alloc_tm,
          caml_alloc_stat,
          caml_start_fiber,
          caml_handle_uncaught_exception,
          caml_buffer,
          caml_buffer_size,
          caml_extract_bytes,
          _initialize}
         = wasmModule.instance.exports;
       start_fiber = make_promising(caml_start_fiber);
       var _initialize = make_promising(_initialize);
       if(globalThis.process?.on)
        globalThis.process.on
         ("uncaughtException",
          (err, _origin)=>caml_handle_uncaught_exception(err));
       else if(globalThis.addEventListener)
        globalThis.addEventListener
         ("error",
          event=>event.error && caml_handle_uncaught_exception(event.error));
       await _initialize();})
  (function(globalThis){"use strict"; return {};}(globalThis))
 ({"link": [["code-7dfd1a6ae59a77d079b5", 0]],
   "generated":
   (globalThis=>{
      var
       joo_global_object = globalThis,
       jsoo_exports = globalThis?.module?.export || globalThis;
      return {"fragments":
              {"get_Array": o=>o.Array,
               "get_Date": o=>o.Date,
               "get_Error": o=>o.Error,
               "get_JSON": o=>o.JSON,
               "get_Math": o=>o.Math,
               "get_Object": o=>o.Object,
               "get_RegExp": o=>o.RegExp,
               "get_String": o=>o.String,
               "js_expr_12c48ca8": ()=>globalThis,
               "meth_call_0_toString": o=>o.toString(),
               "set_mahjongCall": (o, v)=>o.mahjongCall = v}};})
    (globalThis),
   "src": new URL("./engine.assets", import.meta.url).href});
