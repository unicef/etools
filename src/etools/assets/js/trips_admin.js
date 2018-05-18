/**
 * Created by unicef-leb-inn on 5/19/15.
 */

    $(".add-row").on("click", function(){
        alert("text");

        $("div[id*='-depart']").datepicker({
            format: "yyyy-mm-dd",
            todayBtn: "linked",
            autoclose: true,
            todayHighlight: true
        });

        $("div[id*='-arrive']").datepicker({
            format: "yyyy-mm-dd",
            todayBtn: "linked",
            autoclose: true,
            todayHighlight: true
        });

    });



    $('a:contains("Add another Travel Itinerary")').on("click", function(){
        alert("text");

        $("div[id*='-depart']").datepicker({
            format: "yyyy-mm-dd",
            todayBtn: "linked",
            autoclose: true,
            todayHighlight: true
        });

        $("div[id*='-arrive']").datepicker({
            format: "yyyy-mm-dd",
            todayBtn: "linked",
            autoclose: true,
            todayHighlight: true
        });

    });
