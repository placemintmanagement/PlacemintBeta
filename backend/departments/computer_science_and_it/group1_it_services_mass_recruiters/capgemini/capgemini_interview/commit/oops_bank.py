# -*- coding: utf-8 -*-
"""Commit interview OOPs question bank (Capgemini Commit tier only).

9 questions (STATED range: 8-10) -- deeper than Dave's cs.py oops bank
(dave/cs.py is NOT touched or reused here; this is a separate, independent
bank). Covers the 6 topics STATED by name (composition vs inheritance,
dynamic dispatch, upcasting/downcasting, the diamond problem, coupling and
cohesion, SOLID basics) -- SOLID is split across 3 questions (SRP+OCP,
Liskov substitution, ISP+DIP) for actual depth rather than one shallow
five-principle question (INTERPOLATED: the 6 named topics set a floor, not
an exact question count).

Same _kp()/follow_ups pattern as java_bank.py and dave/cs.py: 3-4 key_points
on the main question, exactly 2 fixed follow-ups each with 2-3 key_points.
No model-written questions; the model only grades.
"""
from typing import Any, Dict, List


def _kp(statement: str, *alternatives: str) -> Dict[str, Any]:
    return {"statement": statement, "alternatives": list(alternatives)}


def _fu(text: str, key_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"text": text, "key_points": key_points}


OOPS_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "commit-oops-1", "topic": "oops",
        "text": "What is the difference between composition and inheritance, and how do you decide which to "
                "use?",
        "key_points": [
            _kp("inheritance models an \"is-a\" relationship -- a subclass IS a more specific kind of its "
                "superclass, and automatically acquires the superclass's members",
                "inheritance is an is-a relationship, inheriting members from the base class"),
            _kp("composition models a \"has-a\" relationship -- a class holds a reference to another object "
                "as a field and delegates to it for that behaviour, rather than inheriting it",
                "composition is a has-a relationship built by holding another object and delegating to it"),
            _kp("composition is generally preferred when you just need to reuse behaviour without implying a "
                "true is-a hierarchy, since it's more flexible (can be changed/swapped at runtime) and avoids "
                "tightly coupling classes through a rigid inheritance chain",
                "composition tends to be favoured for reuse because it's looser-coupled and more flexible "
                "than locking in an inheritance relationship"),
        ],
        "follow_ups": [
            _fu("Give a concrete example of a design where inheritance would be a poor fit but composition "
                "would work well.",
                [_kp("gives a specific example where the relationship isn't truly is-a -- e.g. a Car class "
                     "that needs an Engine: a Car is not an Engine, so Car should HOLD an Engine object "
                     "(composition) rather than extend an Engine class (inheritance)",
                     "names a concrete has-a case, such as Car-and-Engine, where composition fits and "
                     "inheritance would misrepresent the relationship"),
                 _kp("explains that extending Engine would also wrongly expose Engine's own public methods "
                     "directly on Car, and would break if Car ever needed to support swapping in a different "
                     "kind of engine at runtime",
                     "inheritance here would leak the engine's interface onto the car and prevent swapping "
                     "engine implementations later")]),
            _fu("What does \"favour composition over inheritance\" actually protect you from, in terms of how "
                "a class hierarchy evolves over time?",
                [_kp("deep or rigid inheritance hierarchies can become fragile -- a change in a base class can "
                     "unexpectedly break many subclasses, and it's hard to change a class's \"kind\" later; "
                     "composition lets you swap out or change the delegated object with less ripple effect",
                     "composition protects against the fragile-base-class problem and makes future changes "
                     "easier to localize"),
                 _kp("inheritance also exposes everything inherited from the base class, even parts a "
                     "subclass doesn't want, whereas composition lets a class expose only the specific "
                     "methods it chooses to delegate",
                     "composition gives more control over which parts of the held object's behaviour are "
                     "actually exposed")]),
        ],
    },
    {
        "id": "commit-oops-2", "topic": "oops",
        "text": "What is dynamic dispatch (virtual method invocation), and why does it matter for "
                "polymorphism?",
        "key_points": [
            _kp("dynamic dispatch means the actual method implementation that runs is determined at runtime, "
                "based on the real/concrete type of the object, not the declared (static) type of the "
                "reference variable",
                "which method body actually executes is decided at runtime by the object's real type"),
            _kp("this is what allows code written against a base type or interface to automatically call the "
                "correct overridden method for whatever subclass the object actually is, without the caller "
                "needing to know or check the concrete type",
                "it's the mechanism that makes calling an overridden method through a base reference work "
                "correctly without explicit type checks"),
            _kp("it's the underlying mechanism that makes runtime polymorphism work, as opposed to static "
                "binding (e.g. overloaded methods or static methods), which is resolved at compile time based "
                "on the declared type",
                "dynamic dispatch is how polymorphism is actually implemented, contrasted with compile-time/"
                "static binding"),
        ],
        "follow_ups": [
            _fu("If a reference is declared as the base type but holds a subclass object, and you call an "
                "overridden method on it, which version runs -- the base class's or the subclass's?",
                [_kp("the subclass's (overriding) version runs, because dispatch is based on the object's "
                     "actual runtime type, not the declared/static type of the reference",
                     "the overridden subclass method runs, since dynamic dispatch looks at the real object "
                     "type"),
                 _kp("the declared/static type of the reference only matters for what the compiler allows "
                     "you to call on it, not for which implementation actually executes at runtime",
                     "the reference's declared type restricts which methods you can call, but doesn't decide "
                     "which implementation runs")]),
            _fu("Is a static method resolved via dynamic dispatch the same way an instance method is? Why or "
                "why not?",
                [_kp("no -- static methods are resolved at compile time based on the reference's declared "
                     "type (static/early binding), not the object's runtime type, so static methods cannot "
                     "truly be overridden/dispatched dynamically the way instance methods can",
                     "static methods use compile-time/static binding, not the runtime dynamic dispatch used "
                     "for instance methods"),
                 _kp("a subclass can declare a static method with the same signature as one in its "
                     "superclass, but that's hiding, not overriding -- which version runs is chosen by the "
                     "reference's declared type, not the object's actual type",
                     "a same-signature static method in a subclass hides rather than overrides the "
                     "superclass's version")]),
        ],
    },
    {
        "id": "commit-oops-3", "topic": "oops",
        "text": "What do upcasting and downcasting mean, and what's the risk with downcasting?",
        "key_points": [
            _kp("upcasting is treating a subclass object through a reference of its superclass or an "
                "interface it implements -- this is always safe and often implicit, since a subclass IS a "
                "kind of its superclass",
                "upcasting treats a more specific object as its more general base type, safely"),
            _kp("downcasting is converting a base-type reference back to a more specific subclass type, which "
                "requires an explicit cast and is only valid if the object actually IS an instance of that "
                "more specific type at runtime",
                "downcasting explicitly casts a general reference back to a specific subclass, which isn't "
                "automatically safe"),
            _kp("downcasting to the wrong type throws a runtime exception (e.g. ClassCastException in Java) "
                "since the check happens at runtime, not compile time -- which is why it's generally "
                "considered a code smell/to be minimized, often checked first (e.g. with instanceof)",
                "an invalid downcast fails at runtime, not compile time, so it's risky and usually "
                "guarded with a type check first"),
        ],
        "follow_ups": [
            _fu("Why is upcasting considered safe while downcasting is not, in terms of what's guaranteed "
                "about the object?",
                [_kp("upcasting never loses validity because every subclass instance genuinely IS a "
                     "superclass instance by definition, so there's nothing to verify; downcasting ASSUMES "
                     "the object is actually of the more specific type, which isn't guaranteed and must be "
                     "checked",
                     "upcasting is guaranteed valid by the is-a relationship itself; downcasting makes an "
                     "assumption that can turn out to be false"),
                 _kp("the compiler can verify upcasting at compile time since it's always safe, but it "
                     "cannot fully verify a downcast at compile time -- the real check has to happen at "
                     "runtime against the object's actual type",
                     "upcasting is checkable statically; downcasting's real validity can only be confirmed "
                     "at runtime")]),
            _fu("How would you write code that attempts a downcast safely, without risking an unhandled "
                "runtime exception?",
                [_kp("check the object's actual type first (e.g. with an instanceof-style check, or a "
                     "language's safe-cast operator that returns null/a sentinel on failure) before "
                     "performing or relying on the cast",
                     "guard the cast with an explicit type check beforehand, or use a cast form that fails "
                     "gracefully instead of throwing"),
                 _kp("alternatively, catch the runtime cast exception (e.g. ClassCastException) around the "
                     "cast and handle the failure case explicitly, rather than letting it propagate "
                     "unhandled",
                     "wrapping the cast in a try/catch for the cast-failure exception is another valid safe "
                     "approach")]),
        ],
    },
    {
        "id": "commit-oops-4", "topic": "oops",
        "text": "What is the diamond problem, and how do languages that support interfaces with default "
                "behaviour, or multiple inheritance, deal with it?",
        "key_points": [
            _kp("the diamond problem arises when a class inherits from two sources that both ultimately "
                "provide the same member (e.g. two parent classes/interfaces that both define a method with "
                "the same signature), creating ambiguity about which implementation the subclass should get",
                "it's the ambiguity that comes from inheriting the same member along two different paths to "
                "a common ancestor"),
            _kp("languages with strict single inheritance of classes (e.g. Java, C#) avoid the classic "
                "diamond for class inheritance entirely by only allowing one base class, but the problem can "
                "resurface through multiple interface implementation once interfaces are allowed to carry "
                "default/implemented methods",
                "single-class-inheritance languages sidestep the classic diamond, but it can reappear via "
                "multiple interfaces with default methods"),
            _kp("the resolution is typically to force the ambiguity to be resolved explicitly -- e.g. Java "
                "requires the implementing class to override the conflicting default method itself rather "
                "than silently picking one of the two inherited versions",
                "the common fix is to make the compiler reject the ambiguity and require an explicit "
                "override/resolution from the programmer"),
        ],
        "follow_ups": [
            _fu("Why don't languages just pick one of the two conflicting implementations automatically "
                "(e.g. \"leftmost parent wins\") instead of forcing the programmer to resolve it?",
                [_kp("an automatic, implicit rule can silently produce behaviour the programmer didn't intend "
                     "or expect, and that behaviour could change unexpectedly if the inheritance order or "
                     "the parent implementations change later -- forcing an explicit resolution makes the "
                     "choice visible and intentional",
                     "an implicit pick-one rule risks silent, surprising, and fragile behaviour, so an "
                     "explicit, compiler-enforced resolution is safer"),
                 _kp("an implicit rule would also hide the fact that there was a genuine conflict at all, "
                     "making it harder for a future maintainer to notice or reason about the ambiguity",
                     "silently resolving it would hide the conflict itself from anyone reading or maintaining "
                     "the code later")]),
            _fu("Does C++ allow true multiple inheritance of classes, and how does that relate to the diamond "
                "problem being a well-known issue there specifically?",
                [_kp("yes, C++ allows a class to inherit from multiple base classes directly, so if two base "
                     "classes share a common ancestor, an object can end up with ambiguous or even duplicated "
                     "copies of that shared ancestor's state, which is exactly the classic diamond problem",
                     "C++'s true multiple class inheritance is why the diamond problem is a well-known, "
                     "concrete issue in that language specifically"),
                 _kp("C++ addresses the duplicated-ancestor-state version of this with virtual inheritance, "
                     "which ensures only one shared copy of the common ancestor exists instead of one copy "
                     "per inheritance path",
                     "C++ offers virtual inheritance specifically to collapse the duplicated base-class copies "
                     "into one shared instance")]),
        ],
    },
    {
        "id": "commit-oops-5", "topic": "oops",
        "text": "What do coupling and cohesion mean, and why do we generally want low coupling and high "
                "cohesion?",
        "key_points": [
            _kp("coupling is how much one module/class depends on or knows about the internal details of "
                "another -- the degree of interconnection between components",
                "coupling measures how dependent/interconnected different components are"),
            _kp("cohesion is how closely related and focused the responsibilities WITHIN a single module/"
                "class are -- whether everything in it serves one clear, unified purpose",
                "cohesion measures how focused a single module's own responsibilities are"),
            _kp("low coupling is desirable because it means a change in one component is less likely to force "
                "changes in unrelated components, and high cohesion is desirable because a focused class is "
                "easier to understand, test, and reuse",
                "low coupling limits the ripple effect of changes; high cohesion keeps classes understandable "
                "and reusable"),
        ],
        "follow_ups": [
            _fu("Give an example of a class with LOW cohesion, and explain what makes it low-cohesion.",
                [_kp("describes a class that bundles several unrelated responsibilities together, e.g. a "
                     "single \"Utils\" or \"Manager\" class that handles logging, database access, and email "
                     "sending all at once, with no single unifying purpose",
                     "names a concrete example, such as a catch-all utility/manager class mixing unrelated "
                     "responsibilities, as low cohesion"),
                 _kp("notes that such a class's methods don't really operate on shared state/data together -- "
                     "they're grouped only by convenience, not by a genuine common purpose",
                     "low cohesion shows up as methods in the class not actually relating to or supporting "
                     "each other")]),
            _fu("How are coupling and cohesion related to each other in practice -- does improving one tend "
                "to help the other?",
                [_kp("they're generally complementary: splitting a low-cohesion class into smaller, "
                     "focused classes (raising cohesion) often naturally reduces how entangled unrelated "
                     "pieces of logic are with each other (lowering coupling) too",
                     "improving cohesion by breaking up unfocused classes tends to also reduce unnecessary "
                     "coupling between the resulting pieces"),
                 _kp("they're not automatically linked though -- it's possible to split a class into many "
                     "small, cohesive pieces that are then so interdependent that coupling actually gets "
                     "worse if the split is done carelessly",
                     "a careless split can raise cohesion of individual pieces while still introducing tight "
                     "coupling between them")]),
        ],
    },
    {
        "id": "commit-oops-6", "topic": "oops",
        "text": "In SOLID, what do the Single Responsibility Principle and the Open/Closed Principle each "
                "mean?",
        "key_points": [
            _kp("Single Responsibility Principle: a class should have only one reason to change -- it should "
                "be responsible for one cohesive piece of functionality, not several unrelated ones",
                "SRP means a class should have a single, focused responsibility/reason to change"),
            _kp("Open/Closed Principle: a class or module should be open for extension but closed for "
                "modification -- you should be able to add new behaviour without changing existing, "
                "already-tested code",
                "OCP means you can extend behaviour without editing the existing class's source"),
            _kp("a common way to follow OCP in practice is through abstraction -- e.g. depending on an "
                "interface/abstract base and adding new behaviour by writing a new implementation of it, "
                "rather than adding more if/else branches to an existing class",
                "OCP is typically achieved via polymorphism/abstraction, adding new implementations rather "
                "than editing existing conditional logic"),
        ],
        "follow_ups": [
            _fu("Give an example of a class that violates the Single Responsibility Principle, and explain "
                "what its multiple responsibilities are.",
                [_kp("describes a concrete class mixing unrelated concerns, e.g. a class that both validates "
                     "user input AND persists it to a database AND formats it for display -- each of those is "
                     "a separate reason the class might need to change",
                     "names a specific class with at least two distinct, unrelated responsibilities/reasons "
                     "to change"),
                 _kp("notes that a change driven by one concern (e.g. a new validation rule) risks "
                     "accidentally affecting or breaking the unrelated concerns bundled into the same class "
                     "(e.g. the persistence or display logic)",
                     "mixing responsibilities means a change to one concern risks unintentionally impacting "
                     "the others in the same class")]),
            _fu("If you need to support a new payment method in a system that currently branches on payment "
                "type with a big if/else chain, how would an Open/Closed-friendly design handle adding that "
                "new type instead?",
                [_kp("define a common interface/abstraction for a payment method, with each payment type as "
                     "its own implementing class, so adding a new payment method means adding a new class "
                     "rather than modifying the existing branching logic",
                     "add a new implementation of a shared payment interface instead of extending an existing "
                     "if/else chain"),
                 _kp("this way the existing, already-tested payment classes and the code that calls them "
                     "through the shared interface don't need to be touched at all to support the new "
                     "payment type",
                     "existing payment implementations and their callers stay unmodified; only a new class is "
                     "added")]),
        ],
    },
    {
        "id": "commit-oops-7", "topic": "oops",
        "text": "In SOLID, what does the Liskov Substitution Principle say, and what's a classic example of "
                "violating it?",
        "key_points": [
            _kp("objects of a subclass should be substitutable for objects of its superclass without "
                "breaking the correctness of the program -- anywhere the base type is expected, a subclass "
                "instance should work correctly in its place",
                "a subtype should be usable anywhere its base type is expected, without breaking behaviour"),
            _kp("violating it typically means a subclass changes or weakens the behaviour the base class's "
                "contract promised -- e.g. throwing an exception for an operation the base class supported, "
                "or silently producing a different/incorrect result",
                "a violation happens when the subclass doesn't honor the behavioural contract of the base "
                "type it claims to be"),
            _kp("the classic example is a Square class extending a Rectangle class and overriding "
                "setWidth/setHeight to keep both sides equal -- this breaks code that relies on a Rectangle's "
                "width and height being independently settable, even though Square is geometrically a kind "
                "of rectangle",
                "the well-known Square-extends-Rectangle example, where forcing equal sides breaks the "
                "base class's assumed independent width/height behaviour"),
        ],
        "follow_ups": [
            _fu("Why is \"Square IS-A Rectangle\" true geometrically but still a poor inheritance design in "
                "code, according to LSP?",
                [_kp("LSP is about behavioural substitutability, not just conceptual/geometric is-a truth -- "
                     "even though a square is geometrically a rectangle, the CODE contract of Rectangle "
                     "(independently settable width and height) isn't honored by Square, so substituting a "
                     "Square wherever a Rectangle is expected can silently break callers",
                     "LSP cares about whether the base class's behavioural contract still holds, not whether "
                     "the is-a relationship is conceptually/geometrically true"),
                 _kp("concretely, code that sets a Rectangle's width and height independently and then "
                     "expects the area to reflect both values correctly would get a silently wrong area if "
                     "handed a Square instead",
                     "gives or implies a concrete scenario, such as a caller independently setting width/"
                     "height and getting a silently incorrect area with a Square")]),
            _fu("How would you redesign the Rectangle/Square relationship to avoid this LSP violation?",
                [_kp("avoid modeling Square as a subclass of a mutable Rectangle at all -- e.g. make shapes "
                     "immutable, or have both Square and Rectangle implement a common Shape-style interface/"
                     "abstraction instead of Square inheriting Rectangle's mutable width/height contract",
                     "break the inheritance relationship itself, e.g. via immutability or a shared interface, "
                     "rather than Square extending Rectangle directly"),
                 _kp("with immutable shapes, there's no setWidth/setHeight to override inconsistently in the "
                     "first place -- a Square and a Rectangle would each just be constructed directly with "
                     "their own valid dimensions",
                     "making shapes immutable removes the mutable setters that caused the contract violation "
                     "to begin with")]),
        ],
    },
    {
        "id": "commit-oops-8", "topic": "oops",
        "text": "In SOLID, what do the Interface Segregation Principle and the Dependency Inversion Principle "
                "each mean?",
        "key_points": [
            _kp("Interface Segregation Principle: clients shouldn't be forced to depend on methods they don't "
                "use -- prefer several small, focused interfaces over one large, general-purpose interface",
                "ISP means splitting large interfaces into smaller, more specific ones so implementers aren't "
                "forced to support methods irrelevant to them"),
            _kp("Dependency Inversion Principle: high-level modules shouldn't depend directly on low-level "
                "modules -- both should depend on abstractions (interfaces), and those abstractions shouldn't "
                "depend on low-level implementation details",
                "DIP means depending on abstractions rather than concrete implementations, for both "
                "high-level and low-level code"),
            _kp("together they push toward designs built around small abstractions that concrete classes "
                "depend on, rather than concrete classes depending directly on each other or on bloated "
                "interfaces",
                "both principles steer a design toward abstraction-centered dependencies rather than direct "
                "concrete coupling"),
        ],
        "follow_ups": [
            _fu("Give an example of an interface that violates ISP, and explain why it forces an implementer "
                "to depend on something it doesn't need.",
                [_kp("describes a \"fat\" interface bundling unrelated operations, e.g. a single Worker "
                     "interface with both work() and eat() methods, which forces a class like a Robot (which "
                     "doesn't eat) to implement a method that's meaningless for it",
                     "names a concrete overly-broad interface, such as a Worker interface forcing a Robot to "
                     "implement an irrelevant eat() method"),
                 _kp("notes that the Robot would then have to provide a meaningless/empty/throwing "
                     "implementation of eat() just to satisfy the interface, which is itself a sign of the "
                     "interface being poorly segregated",
                     "the forced stub/throwing implementation of an irrelevant method is itself the symptom "
                     "of the ISP violation")]),
            _fu("How does Dependency Inversion relate to dependency injection as a concrete coding pattern?",
                [_kp("dependency injection is a common, concrete technique for achieving dependency "
                     "inversion in practice -- instead of a class creating/looking up its own concrete "
                     "dependency, the dependency (typically typed as an interface/abstraction) is passed in "
                     "from outside, e.g. via a constructor",
                     "dependency injection is how DIP is typically implemented: dependencies are supplied "
                     "from outside rather than constructed internally"),
                 _kp("this makes it easy to substitute a different implementation of the dependency (e.g. a "
                     "mock for testing, or a different real implementation later) without changing the "
                     "depending class's own code",
                     "injecting the abstraction makes swapping implementations, including test doubles, "
                     "straightforward")]),
        ],
    },
    {
        "id": "commit-oops-9", "topic": "oops",
        "text": "What is the difference between association, aggregation, and composition as relationships "
                "between classes?",
        "key_points": [
            _kp("association is the most general relationship -- one class simply uses or refers to another "
                "in some way, without implying ownership or a shared lifetime",
                "association is a general \"uses/knows about\" relationship with no ownership implied"),
            _kp("aggregation is a \"has-a\" relationship where one object contains/owns references to others, "
                "but those contained objects can exist independently and outlive the containing object (a "
                "whole-part relationship with independent lifetimes)",
                "aggregation is a has-a relationship where the parts can exist on their own, independent of "
                "the whole"),
            _kp("composition is a stronger \"has-a\" (whole-part) relationship where the contained objects' "
                "lifetimes are tied to the containing object -- when the whole is destroyed, its composed "
                "parts are destroyed/cease to make sense too",
                "composition is a has-a relationship where the parts' lifetime depends on and ends with the "
                "whole"),
        ],
        "follow_ups": [
            _fu("Give an example that's aggregation (not composition), and explain why the contained object's "
                "independent lifetime is what makes it aggregation.",
                [_kp("describes an example like a Department and its Professors -- a Professor can exist and "
                     "move to a different department, so the Department having a list of Professors is "
                     "aggregation, not composition, since the professors don't cease to exist if the "
                     "department is dissolved",
                     "names a concrete case, such as Department-and-Professor, where the parts clearly "
                     "survive independently of the whole"),
                 _kp("notes that the same Professor object could even be referenced by or associated with "
                     "more than one Department at once (e.g. a visiting professor), which a tightly-owned "
                     "composition relationship wouldn't normally allow",
                     "the shared/independent object could plausibly belong to or be referenced from more "
                     "than one container, unlike a composed part")]),
            _fu("Give an example that's composition (not aggregation), and explain why the part's lifetime is "
                "genuinely tied to the whole.",
                [_kp("describes an example like a House and its Rooms (or a Car and its Engine, if modeled as "
                     "non-removable) -- the Rooms don't have independent existence or meaning once the House "
                     "they belong to is gone, so their lifetime is bound to the House's",
                     "names a concrete case, such as House-and-Room, where the part has no independent "
                     "existence once the whole is destroyed"),
                 _kp("notes that a Room object wouldn't typically be created or referenced independently of "
                     "its House at all -- it's usually owned exclusively, often created as part of creating "
                     "the House itself",
                     "the composed part is exclusively owned and typically doesn't exist or get created "
                     "outside the whole")]),
        ],
    },
]
