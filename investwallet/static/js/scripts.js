document.addEventListener("DOMContentLoaded", function () {
    const selects = document.querySelectorAll(".select2-papeis");

    selects.forEach(function (select) {
        const modalSelector = select.getAttribute("data-modal");
        $(select).select2({
            dropdownParent: $(modalSelector),
            width: "100%",
            language: {
                noResults: function () {
                    return "Nenhum papel encontrado";
                },
            },
        });
    });
});

