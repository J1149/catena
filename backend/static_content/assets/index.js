import "./css/styles.css"
import {v4 as uuidv4} from 'uuid';
import 'jquery';
import 'popper.js';
import 'bootstrap';
import Stepper from 'bs-stepper'
import Cropper from 'cropperjs';
import Viewer from 'viewerjs';
import Cookies from 'js-cookie';
import 'bootstrap-toggle';

var cropper = null;
var viewer = null;


function onDeleteAsset(assetId) {
    let csrftoken = Cookies.get('csrftoken');

    return () => fetch(`/assets/${assetId}/`, {
        credentials: 'include',
        cache: 'no-cache',
        redirect: 'follow',
        method: 'DELETE',
        headers: {"X-CSRFToken": csrftoken},
    }).then(data => {
        window.location.replace('/assets')
    })
};

function onEditAsset(assetId) {
    return () => {
        window.location.replace(`/assets/edit/${assetId}/`)
    }
};


$('#assetModal').on('show.bs.modal', function (event) {
    const button = $(event.relatedTarget) // Button that triggered the modal
    const assetOwner = button.data('asset-owner')
    const modalTitle = button.data('asset-artist')
    const assetId = button.data('asset-id')
    const artworkName = button.data('asset-name')
    const description = button.data('asset-description')
    const images = button.data('asset-images')
    const price = button.data('asset-price')
    const primaryImage = button.data('primary-image')
    const assetOwnerDmUrl = button.data('owner-dm-url')
    const assetOwnerProfileUrl = button.data('owner-profile-url')
    const assetTxid = button.data('asset-txid')
    const assetTxidUrl = button.data('asset-txid-url')
    const modal = $(this)
    modal.find('.modal-title').text(modalTitle)

    modal.find('.modal-body #artworkName').text(artworkName)
    modal.find('.modal-body #primaryImage').attr('src', primaryImage)
    const replaced = images.replaceAll("'", '"')
    for (const image_src of JSON.parse(replaced)) {
        modal.find('.modal-body #modal-gallery').append(`<li><img src="${image_src}"></li>`)
    }
    const imageGallery = document.getElementById('modal-gallery')
    if (viewer) {
        viewer = null;
    }
    viewer = new Viewer(imageGallery, {inline: false})

    modal.find('.modal-body #asset-images').val(images)
    modal.find('.modal-body #assetDescription').text(description)
    modal.find('#assetPrice').text(`\$${price}`)
    modal.find('.modal-body #assetUserProfileUrl').text(assetOwner)
    modal.find('.modal-body #assetUserProfileUrl').attr('href', assetOwnerProfileUrl)


    const buttonsDiv = modal.find('#asset-modal-buttons');

    const transactionIdDiv = modal.find('#transactionIdDiv')
    transactionIdDiv.append(`<p>Transaction ID:</p>`);
    if (assetTxid === 'Transaction Id Not Found') {

        transactionIdDiv.append(`<i id="assetTxid">${assetTxid}</i>`)
    } else {
        transactionIdDiv.append(`<a target=_blank id="assetTxid" href="${assetTxidUrl}">${assetTxid}</a>`)
    }

    //modal.find('.modal-body #assetTxid').text(assetTxid)

    buttonsDiv.append(`<button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>`)
    if (assetOwner === 'self') {
        // Delete button
        buttonsDiv.append(`<a id="deleteAssetButton" type="button" class="btn modal-btn-delete">Delete Asset</a>`)
        modal.find('#deleteAssetButton').click(onDeleteAsset(assetId))
        // Edit button
        buttonsDiv.append(`<a id="editAssetButton" type="button" class="btn btn-secondary">Edit Asset</a>`)
        modal.find('#editAssetButton').click(onEditAsset(assetId))
    } else {
        buttonsDiv.append(`<a id="sendMessageButton" type="button" class="btn btn-secondary">Send message</a>`)
        modal.find('.modal-footer #sendMessageButton').attr('href', assetOwnerDmUrl)

    }


})
$('#assetModal').on('hidden.bs.modal', function (e) {
    if (e.target.id === 'assetModal') {
        viewer.destroy();
        const modal = $(this)
        modal.find('.modal-body #modal-gallery').html("")
        modal.find('#asset-modal-buttons').html("")
        modal.find('#transactionIdDiv').html("")

    }
})

function deleteChildren(node) {
    let last;
    while (last = node.lastChild)
        node.removeChild(last);
}

function getImgUuid() {
    return `img-${uuidv4()}`;
}

function addCropper(assetImg, imgId) {
    cropper = new Cropper(assetImg, {aspectRatio: 1 / 1})
    cropper.id = 'add-asset-cropper'
    // let iimg = $(`#${imgId}`);
    // iimg.on('cropend', (event) => {
    //     //console.log('cropend', event)
    //     console.log('cropend', event.detail.action)
    // })
    // iimg.on('cropmove', (event) => {
    //     //console.log('cropend', event)
    //     console.log('cropmove', event.detail.action)
    // })
    // iimg.on('zoom', (event) => {
    //     //console.log('cropend', event)
    //     console.log('zoom', event.detail.action)
    // })
}


function onAddAssetSubmit(form) {
    return (event) => {
        console.log(`Form submitted! Time stamp: ${event.timeStamp}`);
        event.preventDefault();
        const formData = new FormData(form)
        const croppedCanvas = cropper.getCroppedCanvas();

        croppedCanvas.toBlob((blob) => {
            formData.append('thumbnail', blob, 'thumbnail.png')
            fetch('', {
                credentials: 'include',
                cache: 'no-cache',
                redirect: 'follow',
                method: 'POST',
                body: formData
            }).then(data => {
                window.location.replace('/assets')

            })
        })
    }
}

function onRefreshProfile() {
    let csrftoken = Cookies.get('csrftoken');
    return fetch('/users/refresh-profile/', {
        credentials: 'include',
        cache: 'no-cache',
        redirect: 'follow',
        method: 'POST',
        headers: {"X-CSRFToken": csrftoken},

    })
}

const addAssetForm = document.getElementById('add-asset-form')

if (addAssetForm) {
    addAssetForm.addEventListener('submit', onAddAssetSubmit(addAssetForm))
    $(function () {
        $('#publiclyViewableCheckbox').bootstrapToggle();
    })

}


const profileForm = document.getElementById('profile-form')

if (profileForm) {
    profileForm.addEventListener('click', onRefreshProfile)
}


function addAsset(toThumbnailDiv, toConsiderDiv) {
    return function (e) {
        // one level of indirection to return the image
        let assetImg = document.createElement('img')
        assetImg.setAttribute('src', e.target.result)
        const imgId = getImgUuid()
        assetImg.setAttribute('id', imgId)

        let onAssetImgClick = function () {
            // move the current img from toThumbnail to toConsider
            //toConsiderDiv.appendChild(toThumbnailDiv.lastChild)
            deleteChildren(toThumbnailDiv);
            // remove the future image from toConsider
            //assetImg.parentNode.removeChild(assetImg)
            // Add it to toThumbnail
            const clone = assetImg.cloneNode();
            toThumbnailDiv.appendChild(clone);
            // wrap it in a cropper
            addCropper(clone, imgId)
        }

        toConsiderDiv.appendChild(assetImg);

        let iimg = $(`#${imgId}`);
        iimg.click(onAssetImgClick)
        return assetImg;
    }
}

function onAssetImgsUploadChange(input) {
    if (!(input.files && input.files[0])) {
        return
    }

    const toConsiderDiv = document.getElementById('add-asset-to-thumbnail-to-consider');
    const toThumbnailDiv = document.getElementById('add-asset-to-thumbnail');
    // remove all old images
    deleteChildren(toConsiderDiv);
    deleteChildren(toThumbnailDiv)

    let onloadFn = function (e) {
        addAsset(toThumbnailDiv, toConsiderDiv)(e)
    }

    let onLoadForCropperFn = function (e) {
        addAsset(toThumbnailDiv, toConsiderDiv)(e);
        deleteChildren(toThumbnailDiv);
        let assetImg = document.createElement('img')
        const imgId = getImgUuid()
        assetImg.setAttribute('id', imgId)
        assetImg.setAttribute('src', e.target.result)
        toThumbnailDiv.appendChild(assetImg)
        addCropper(assetImg, imgId)

    }


    let firstImage = true;
    for (const fyle of input.files) {
        const reader = new FileReader();
        if (firstImage) {
            reader.onload = onLoadForCropperFn;
            firstImage = false;
        } else {
            reader.onload = onloadFn;
        }
        reader.readAsDataURL(fyle);
    }
}

$("#assetImgUploads").change(function () {
    onAssetImgsUploadChange(this);
});


$(document).ready(function () {
    console.log(1)
    if ($('.add-asset-nxt-btn').length) {
        const stepper1 = new Stepper($('.bs-stepper')[0])
        $('.add-asset-nxt-btn').click(function () {
            stepper1.next();
        })
        $('.add-asset-prev-btn').click(function () {
            stepper1.previous();
        })
    }

    // landing page

    $(window).bind('scroll', function (e) {
        dotnavigation();
    });

    function dotnavigation() {

        var numSections = $('.landing-image-container').length;

        $('#dot-nav li a').removeClass('active').parent('li').removeClass('active');
        // console.log($('section'))
        // console.log('$(\'section\').length',$('section').length)
        $('.landing-image-container').each(function (i, item) {
            var ele = $(item), nextTop;
            console.log(ele)
            if (typeof ele.next().offset() != "undefined") {
                nextTop = ele.next().offset().top;
            } else {
                nextTop = $(document).height();
            }
            var thisTop = 0;
            if (ele.offset() !== null) {
                thisTop = ele.offset().top - ((nextTop - ele.offset().top - 500) / numSections);
            } else {
                thisTop = 0;
            }

            var docTop = $(document).scrollTop();

            if (docTop >= thisTop && (docTop < nextTop)) {
                $('#dot-nav li').eq(i).addClass('active');
            }
        });
    }

    /* get clicks working */
    $('#dot-nav li').click(function () {
        console.log('click')
        var id = $(this).find('a').attr("href"),
            posi,
            ele,
            padding =0;

        ele = $(id);
        console.log('ele', ele)
        console.log('id', id)
        posi =  ($(ele).offset() ).top - padding;// $(document).scrollTop();//$(document).height();//Math.ceil((window.innerHeight * 50 / 100)); //($(ele).offset() ).top - padding;
        console.log('ele', ele)
        console.log('posi', posi )
        console.log('id', id)
        var res = $('html, body').animate({scrollTop: posi}, 200,'linear');
        console.log(res)

        return false;
    });
    //end landing page

})



