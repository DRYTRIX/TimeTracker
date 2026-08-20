/* Minimal signature capture used by the client portal quote page. */
(function (global) {
    function SignaturePad(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext("2d");
        this.drawing = false;
        this._empty = true;
        this._resize();
        canvas.addEventListener("pointerdown", this._down.bind(this));
        canvas.addEventListener("pointermove", this._move.bind(this));
        canvas.addEventListener("pointerup", this._up.bind(this));
        canvas.addEventListener("pointerleave", this._up.bind(this));
    }
    SignaturePad.prototype._resize = function () {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        this.canvas.width = this.canvas.offsetWidth * ratio;
        this.canvas.height = this.canvas.offsetHeight * ratio;
        this.ctx.scale(ratio, ratio);
        this.ctx.strokeStyle = "#111";
        this.ctx.lineWidth = 2;
        this.ctx.lineCap = "round";
    };
    SignaturePad.prototype._pos = function (e) {
        const rect = this.canvas.getBoundingClientRect();
        return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };
    SignaturePad.prototype._down = function (e) {
        this.drawing = true;
        const p = this._pos(e);
        this.ctx.beginPath();
        this.ctx.moveTo(p.x, p.y);
        this.canvas.setPointerCapture(e.pointerId);
    };
    SignaturePad.prototype._move = function (e) {
        if (!this.drawing) return;
        const p = this._pos(e);
        this.ctx.lineTo(p.x, p.y);
        this.ctx.stroke();
        this._empty = false;
    };
    SignaturePad.prototype._up = function () {
        this.drawing = false;
    };
    SignaturePad.prototype.clear = function () {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this._empty = true;
    };
    SignaturePad.prototype.isEmpty = function () {
        return this._empty;
    };
    SignaturePad.prototype.toDataURL = function () {
        return this.canvas.toDataURL("image/png");
    };
    global.SignaturePad = SignaturePad;
})(window);
