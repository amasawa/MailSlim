# Email Deletion Rules

---

## Delete

Emails matching ANY of the following conditions should be flagged for deletion:

### By keyword (subject or body)
- unsubscribe, promotion, sale, discount, coupon, deal, newsletter, marketing

### By sender pattern
- noreply@*, no-reply@*, notifications@*, marketing@*, promo@*

### By category
- Social media notifications (e.g. likes, follows, comments, friend requests)
- Verification codes / OTP / password reset emails (including flychinaeastern/ceair.com)
- Shipping / delivery / logistics tracking notifications
- Review invitations / peer review requests (e.g. "invitation to review", "review request", "referee request")

### By folder
- All emails in Spam / Junk folder

### By sender name (partial match)
- alphaXiv
- IEEE Membership, IEEE eNotice, IEEE-HKN, IEEE Xplore Team, IEEE Spectrum
- Starbucks
- IntechOpen
- SlidesLive
- Trip.com
- LinkedIn
- Afterpay
- Uber
- world-comp.org
- Flybuys
- Beara Beara (bearabeara)
- Funlab, Strike (fun-lab.com)
- HSBC marketing (messaging.hsbc.com.au, ealerts@notification.hsbc)
- Aquarian Pearls
- Crunch Hospo (divcom.net.au)
- Apple Developer / Apple Market Research (insideapple.apple.com)
- Worlds4 (worlds4.co.uk) — predatory conference
- Kennedy@iccvais.com — predatory conference
- iuyuynee@fhysxq.top — spam
- Geological@alsobro.com — predatory conference
- kuajing@service.netease.com — 网易跨境电商营销
- ActivateFit.Gym (activatefit.gym)





---

## Not Delete

Emails matching ANY of the following conditions must NEVER be deleted, even if they match a Delete rule above:

### By sender domain
- *@sydney.edu.au (The University of Sydney)
- *@uni.sydney.edu.au
- *@*.edu, *@*.edu.* (any .edu domain — universities, academic institutions)

### By sender name / platform (partial match)
- wanchunliu
- longbingcao
- chairingtool.com (conference chairing tool)
- msr-cmt.org (Microsoft CMT conference management)
- openreview (OpenReview.net)
- springer, nature (Springer Nature journals)
- elsevier, sciencedirect (Elsevier journals)
- wiley (Wiley journals)
- ieee (IEEE — conference/journal correspondence, NOT newsletters)
- acm, dl.acm.org (ACM Digital Library)
- mdpi (MDPI journals)
- arxiv (arXiv notifications)
- aaai, neurips, nips, icml, iclr, cvpr, eccv, iccv, emnlp, acl (top conferences)

### By content type
- Emails with attachments

### By category
- Invoices, receipts, payment confirmations, billing statements
- Work-related correspondence
- Financial / tax documents
- Paper submissions, acceptance/rejection decisions, camera-ready notifications
- Conference registrations, author notifications
