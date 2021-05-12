$(function() {

    const url = "http://3445144jk7.wicp.vip:30000";
    const k = 10;

    var name = "none";
    var rotate = false;
    var zoom = 3;
    var buffer = null;
    var rx = 0;
    var ry = 270;
    var lastx = -1;
    var lasty = -1;

    $(".box_1").mousedown(function(e) {
        e.preventDefault();
        rotate = true;
    });

    $(".box_1").mouseup(function(e) {
        e.preventDefault();
        rotate = false;
        lastx = lasty = -1;

        //请求最终停留位置的上下级缓存
        let request = {
            type: "zoom",
            exit: false,
            rx: rx,
            ry: ry,
            zoom: zoom,
            more: false,
            less: false
        };

        if (zoom !== 10 && !buffer[rx][ry].exist[zoom]) {
            request.more = true;
        }

        if (zoom !== 1 && !buffer[rx][ry].exist[zoom - 2]) {
            request.less = true;
        }

        request = JSON.stringify(request);

        showloading();
        fetch(url, {
            method: 'POST',
            mode: 'cors',
            headers: {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'text/plain',
                'Content-Length': request.length
            },
            body: request
        }).then(res => res.json()).then(res => {
            if (res.more !== undefined) {
                buffer[rx][ry].exist[zoom] = true;
                buffer[rx][ry].data[zoom] = res.more;
            }

            if (res.less !== undefined) {
                buffer[rx][ry].exist[zoom - 2] = true;
                buffer[rx][ry].data[zoom - 2] = res.less;
            }
        }).then(() => {
            hideloading();
        }).catch((err) => {
            console.log("zoom buffer request fail: ", err);
            hideloading();
        })
    });

    $(".box_1").on("mousewheel", zoomListen);
    $(".box_1").on("mousemove", rotateListen);

    $("#type").change(function(e) {
        e.preventDefault();
        let newName = this.value;

        showloading();

        //关闭前一个链接
        if (name !== "none") {
            let request = {
                exit: true
            }

            request = JSON.stringify(request);

            fetch(url, {
                method: 'POST',
                mode: 'cors',
                headers: {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'text/plain',
                    'Content-Length': request.length
                },
                body: request
            }).then(res => {
                //开启新链接
                startNew(newName);
            }).catch((err) => {
                console.log("[Err:]Last program didn't close successfully.")
                hideloading();
            })
        } else {
            startNew(newName);
        }


        function startNew(newName) {
            init();
            name = newName;

            if (name !== "none") {
                //建立新的链接
                fetch(url + "/" + newName, {
                    method: 'GET',
                    mode: 'cors',
                    headers: {
                        'Access-Control-Allow-Origin': '*'
                    }
                }).then(res => res.json()).then(res => {
                    //初始数据
                    buffer[rx][ry].exist[zoom - 1] = true;
                    buffer[rx][ry].data[zoom - 1] = res.data;

                    //下一级缓存
                    buffer[rx][ry].exist[zoom - 2] = true;
                    buffer[rx][ry].data[zoom - 2] = res.less;

                    //上一级缓存
                    buffer[rx][ry].exist[zoom] = true;
                    buffer[rx][ry].data[zoom] = res.more
                    $("#image").attr("src", "data:image/png;base64," + res.data)
                    hideloading();
                }).catch((err) => {
                    console.log("[Err:]Program didn't start successfully.")
                    hideloading();
                })
            } else {
                hideloading();
            }
        }
    });

    function rotateListen(e) {
        e.preventDefault();
        let x = e.clientX;
        let y = e.clientY;

        if (rotate) {
            if (lastx !== -1 && lasty !== -1) {
                let deltax = -(x - lastx);
                let deltay = -(y - lasty);
                let d = distance(x, y, lastx, lasty);
                if (d < k) {
                    return false;
                }


                rx += parseInt(deltax / k);
                rx = rx < 0 ? 360 + rx : rx;
                rx = rx >= 360 ? rx - 360 : rx;

                ry += parseInt(deltay / k);
                ry = ry < 0 ? 360 + ry : ry;
                ry = ry >= 360 ? ry - 360 : ry;

                //缓存命中
                if (buffer[rx][ry].exist[zoom - 1]) {
                    console.log("hit")
                    $("#image").attr("src", "data:image/png;base64," + buffer[rx][ry].data[zoom - 1]);
                    $(".box_1").off("mousemove", rotateListen);
                    showloading();

                    //请求缓存
                    let request = {
                        type: "rotate",
                        exit: false,
                        miss: false,
                        rx: rx,
                        ry: ry,
                        zoom: zoom
                    }

                    request = JSON.stringify(request);

                    //请求：下一个预测点数据、当前点的缩放缓存数据（如果没有的话）
                    fetch(url, {
                        method: 'POST',
                        mode: 'cors',
                        headers: {
                            'Access-Control-Allow-Origin': '*',
                            'Content-Type': 'text/plain',
                            'Content-Length': request.length
                        },
                        body: request
                    }).then(res => res.json()).then(res => {
                        let next = res.next;
                        if (next.flag === 0) {
                            buffer[next.rx][next.ry].exist[zoom - 1] = true;
                            buffer[next.rx][next.ry].data[zoom - 1] = next.data;
                        }
                    }).then(() => {
                        $(".box_1").on("mousemove", rotateListen);
                        hideloading();
                    }).catch((err) => {
                        console.log("rotate buffer request fail: ", err);
                        $(".box_1").on("mousemove", rotateListen);
                        hideloading();
                    })

                } else {
                    $(".box_1").off("mousemove", rotateListen);
                    console.log("miss")
                    showloading();

                    //请求未命中
                    let request = {
                        type: "rotate",
                        exit: false,
                        miss: true,
                        rx: rx,
                        ry: ry,
                        zoom: zoom
                    }

                    request = JSON.stringify(request);

                    //请求：当前点的数据、当前点的缩放缓存数据（如果没有的话）、下一预测点的数据
                    fetch(url, {
                        method: 'POST',
                        mode: 'cors',
                        headers: {
                            'Access-Control-Allow-Origin': '*',
                            'Content-Type': 'text/plain',
                            'Content-Length': request.length
                        },
                        body: request
                    }).then(res => res.json()).then(res => {
                        buffer[rx][ry].exist[zoom - 1] = true;
                        buffer[rx][ry].data[zoom - 1] = res.data;
                        $("#image").attr("src", "data:image/png;base64," + res.data);

                        let next = res.next;
                        if (next.flag === 0) {
                            buffer[next.rx][next.ry].exist[zoom - 1] = true;
                            buffer[next.rx][next.ry].data[zoom - 1] = next.data;
                        }
                    }).then(() => {
                        $(".box_1").on("mousemove", rotateListen);
                        hideloading();
                    }).catch(err => {
                        console.log("rotate miss request fail: ", err);
                        $(".box_1").on("mousemove", rotateListen);
                        hideloading();
                    })
                }
            }
            lastx = x;
            lasty = y;
        }
    };

    function zoomListen(e) {
        let delta = -e.originalEvent.deltaY;
        let origin_zoom = zoom;

        // delta大于0为放大，反之为缩小
        if (delta > 0) {
            zoom = zoom + 1 > 10 ? 10 : zoom + 1;
        } else {
            zoom = zoom - 1 < 1 ? 1 : zoom - 1;
        }

        //发生了变化
        if (origin_zoom !== zoom) {
            //阻塞监听函数，防止因网速慢导致的异步错误
            $(".box_1").off("mousewheel", zoomListen);

            //不可能miss
            $("#image").attr("src", "data:image/png;base64," + buffer[rx][ry].data[zoom - 1]);

            //请求新缓存
            let request = {
                type: "zoom",
                exit: false,
                rx: rx,
                ry: ry,
                zoom: zoom,
                more: false,
                less: false
            };

            // 是否需要请求缓存
            let flag = false;

            if (delta > 0 && zoom !== 10 && !buffer[rx][ry].exist[zoom]) {
                request.more = true;
                flag = true;
            }

            if (delta < 0 && zoom !== 1 && !buffer[rx][ry].exist[zoom - 2]) {
                request.less = true;
                flag = true;
            }

            request = JSON.stringify(request);

            if (flag) {
                showloading();
                fetch(url, {
                    method: 'POST',
                    mode: 'cors',
                    headers: {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'text/plain',
                        'Content-Length': request.length
                    },
                    body: request
                }).then(res => res.json()).then(res => {
                    if (delta > 0) {
                        buffer[rx][ry].exist[zoom] = true;
                        buffer[rx][ry].data[zoom] = res.more;
                    } else {
                        buffer[rx][ry].exist[zoom - 2] = true;
                        buffer[rx][ry].data[zoom - 2] = res.less;
                    }
                }).then(() => {
                    $(".box_1").on("mousewheel", zoomListen);
                    hideloading();
                }).catch((err) => {
                    console.log("zoom buffer request fail: ", err);
                    $(".box_1").on("mousewheel", zoomListen);
                    hideloading();
                })
            } else {
                $(".box_1").on("mousewheel", zoomListen);
            }
        }
    }

    function init() {
        buffer = new Array(360);
        for (let i = 0; i < 360; i++) {
            buffer[i] = new Array(360);
            for (let j = 0; j < 360; j++) {
                let exist = new Array(10);
                exist.fill(false);
                let data = new Array(10);
                data.fill("");
                buffer[i][j] = {
                    exist: exist,
                    data: data
                }
            }
        }

        rx = 0;
        ry = 270;
        zoom = 3;
        $("#image").attr("src", "");
    }

    function showloading() {
        $(".container").css("visibility", 'visible')
    }

    function hideloading() {
        $(".container").css("visibility", 'hidden')
    }

    function distance(x1, y1, x2, y2) {
        return parseInt(Math.sqrt(Math.pow((x1 - x2), 2) + Math.pow((y1 - y2), 2)));
    }
})